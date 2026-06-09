#include "codexion.h"

// ----------------------------------------------------------------------------
// Utilities
// ----------------------------------------------------------------------------

long long get_current_ms(void)
{
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (long long)tv.tv_sec * 1000 + tv.tv_usec / 1000;
}

void log_message(t_sim *sim, long long timestamp, int coder_id, const char *action)
{
    pthread_mutex_lock(&sim->log_mutex);
    // FIX: suppress all non-burnout messages after stop_flag
    if (sim->stop_flag && strcmp(action, "burned out") != 0)
    {
        pthread_mutex_unlock(&sim->log_mutex);
        return;
    }
    printf("%lld %d %s\n", timestamp - sim->sim_start_ms, coder_id, action);
    fflush(stdout);
    pthread_mutex_unlock(&sim->log_mutex);
}

// FIX: interruptible sleep using stop condition variable
int interruptible_sleep(t_sim *sim, int ms)
{
    struct timespec ts;
    pthread_mutex_lock(&sim->stop_mutex);
    long long end = get_current_ms() + ms;
    while (!sim->stop_flag && get_current_ms() < end)
    {
        long long remaining = end - get_current_ms();
        if (remaining <= 0) break;
        ts.tv_sec = remaining / 1000;
        ts.tv_nsec = (remaining % 1000) * 1000000;
        pthread_cond_timedwait(&sim->stop_cond, &sim->stop_mutex, &ts);
    }
    int stopped = sim->stop_flag;
    pthread_mutex_unlock(&sim->stop_mutex);
    return stopped;
}

// ----------------------------------------------------------------------------
// Heap (priority queue) implementation
// ----------------------------------------------------------------------------

void heap_swap(t_heap_node *a, t_heap_node *b)
{
    t_heap_node tmp = *a;
    *a = *b;
    *b = tmp;
}

void heap_init(t_heap *h, int (*cmp)(t_heap_node, t_heap_node))
{
    h->arr = NULL;
    h->size = 0;
    h->capacity = 0;
    h->cmp = cmp;
}

void heap_push(t_heap *h, t_heap_node node)
{
    if (h->size >= h->capacity)
    {
        int new_cap = (h->capacity == 0) ? 4 : h->capacity * 2;
        t_heap_node *new_arr = realloc(h->arr, new_cap * sizeof(t_heap_node));
        if (!new_arr)
            return;
        h->arr = new_arr;
        h->capacity = new_cap;
    }
    int idx = h->size++;
    h->arr[idx] = node;
    while (idx > 0)
    {
        int parent = (idx - 1) / 2;
        if (h->cmp(h->arr[idx], h->arr[parent]))
        {
            heap_swap(&h->arr[idx], &h->arr[parent]);
            idx = parent;
        }
        else
            break;
    }
}

t_heap_node heap_pop(t_heap *h)
{
    t_heap_node top = h->arr[0];
    h->arr[0] = h->arr[--h->size];
    int idx = 0;
    while (1)
    {
        int left = idx * 2 + 1;
        int right = idx * 2 + 2;
        int largest = idx;
        if (left < h->size && h->cmp(h->arr[left], h->arr[largest]))
            largest = left;
        if (right < h->size && h->cmp(h->arr[right], h->arr[largest]))
            largest = right;
        if (largest != idx)
        {
            heap_swap(&h->arr[idx], &h->arr[largest]);
            idx = largest;
        }
        else
            break;
    }
    return top;
}

t_heap_node *heap_peek(t_heap *h)
{
    if (h->size == 0)
        return NULL;
    return &h->arr[0];
}

int heap_is_empty(t_heap *h)
{
    return h->size == 0;
}

void heap_free(t_heap *h)
{
    free(h->arr);
    h->arr = NULL;
    h->size = 0;
    h->capacity = 0;
}

int compare_fifo(t_heap_node a, t_heap_node b)
{
    if (a.key != b.key)
        return a.key < b.key;
    return a.coder_id < b.coder_id;
}

int compare_edf(t_heap_node a, t_heap_node b)
{
    if (a.key != b.key)
        return a.key < b.key;
    // FIX: tie-breaker – higher coder_id gets priority (as requested)
    return a.coder_id > b.coder_id;
}

// ----------------------------------------------------------------------------
// Dongle operations
// ----------------------------------------------------------------------------

int dongle_acquire(t_sim *sim, t_dongle *d, int coder_id, long long key)
{
    pthread_mutex_lock(&d->mutex);
    t_heap_node node = {coder_id, key};
    heap_push(&d->wait_queue, node);

    while (!sim->stop_flag)
    {
        t_heap_node *top = heap_peek(&d->wait_queue);
        if (top && top->coder_id == coder_id &&
            d->in_use == 0 && get_current_ms() >= d->cooldown_until)
        {
            heap_pop(&d->wait_queue);
            d->in_use = 1;
            pthread_mutex_unlock(&d->mutex);
            return 0;
        }
        long long now = get_current_ms();
        long long wait_until = d->cooldown_until;
        if (wait_until <= now)
            wait_until = now + 10;
        struct timespec ts;
        ts.tv_sec = wait_until / 1000;
        ts.tv_nsec = (wait_until % 1000) * 1000000;
        pthread_cond_timedwait(&d->cond, &d->mutex, &ts);
    }

    // Remove self from queue on stop
    for (int i = 0; i < d->wait_queue.size; i++)
    {
        if (d->wait_queue.arr[i].coder_id == coder_id)
        {
            d->wait_queue.arr[i] = d->wait_queue.arr[--d->wait_queue.size];
            int idx = i;
            while (idx > 0)
            {
                int parent = (idx - 1) / 2;
                if (d->wait_queue.cmp(d->wait_queue.arr[idx], d->wait_queue.arr[parent]))
                {
                    heap_swap(&d->wait_queue.arr[idx], &d->wait_queue.arr[parent]);
                    idx = parent;
                }
                else
                    break;
            }
            while (1)
            {
                int left = idx * 2 + 1;
                int right = idx * 2 + 2;
                int largest = idx;
                if (left < d->wait_queue.size && d->wait_queue.cmp(d->wait_queue.arr[left], d->wait_queue.arr[largest]))
                    largest = left;
                if (right < d->wait_queue.size && d->wait_queue.cmp(d->wait_queue.arr[right], d->wait_queue.arr[largest]))
                    largest = right;
                if (largest != idx)
                {
                    heap_swap(&d->wait_queue.arr[idx], &d->wait_queue.arr[largest]);
                    idx = largest;
                }
                else
                    break;
            }
            break;
        }
    }
    pthread_mutex_unlock(&d->mutex);
    return -1;
}

void dongle_release(t_sim *sim, t_dongle *d)
{
    pthread_mutex_lock(&d->mutex);
    d->in_use = 0;
    d->cooldown_until = get_current_ms() + sim->dongle_cooldown;
    pthread_cond_broadcast(&d->cond);
    pthread_mutex_unlock(&d->mutex);
}

// ----------------------------------------------------------------------------
// Coder thread
// ----------------------------------------------------------------------------

void *coder_routine(void *arg)
{
    t_thread_arg *thread_arg = (t_thread_arg *)arg;
    t_sim *sim = thread_arg->sim;
    int coder_id = thread_arg->coder_id;
    free(arg);

    t_coder *coder = &sim->coders[coder_id - 1];
    t_dongle *left = &sim->dongles[coder->left_dongle_id - 1];
    t_dongle *right = &sim->dongles[coder->right_dongle_id - 1];

    t_dongle *first, *second;
    if (coder->left_dongle_id < coder->right_dongle_id)
    {
        first = left;
        second = right;
    }
    else
    {
        first = right;
        second = left;
    }

    while (!sim->stop_flag && coder->compiles_done < sim->compiles_required)
    {
        long long key;
        if (sim->scheduler == 0)
            key = get_current_ms();                     // FIFO: request time
        else
            key = coder->last_compile_start + sim->time_to_burnout; // EDF: deadline

        if (dongle_acquire(sim, first, coder_id, key) == -1)
            break;
        log_message(sim, get_current_ms(), coder_id, "has taken a dongle");

        if (dongle_acquire(sim, second, coder_id, key) == -1)
        {
            dongle_release(sim, first);
            break;
        }
        log_message(sim, get_current_ms(), coder_id, "has taken a dongle");

        long long compile_start = get_current_ms();
        log_message(sim, compile_start, coder_id, "is compiling");
        coder->last_compile_start = compile_start;
        // FIX: use interruptible sleep
        if (interruptible_sleep(sim, sim->time_to_compile))
        {
            // stop_flag set during compile – release dongles and exit
            dongle_release(sim, first);
            dongle_release(sim, second);
            break;
        }
        dongle_release(sim, first);
        dongle_release(sim, second);
        coder->compiles_done++;

        if (sim->stop_flag)
            break;

        log_message(sim, get_current_ms(), coder_id, "is debugging");
        if (interruptible_sleep(sim, sim->time_to_debug))
            break;

        if (sim->stop_flag)
            break;

        log_message(sim, get_current_ms(), coder_id, "is refactoring");
        if (interruptible_sleep(sim, sim->time_to_refactor))
            break;
    }
    return NULL;
}

// ----------------------------------------------------------------------------
// Monitor thread
// ----------------------------------------------------------------------------

void *monitor_routine(void *arg)
{
    t_sim *sim = (t_sim *)arg;

    while (!sim->stop_flag)
    {
        long long now = get_current_ms();
        for (int i = 0; i < sim->num_coders; i++)
        {
            if (now - sim->coders[i].last_compile_start >= sim->time_to_burnout)
            {
                pthread_mutex_lock(&sim->stop_mutex);
                if (!sim->stop_flag)
                {
                    sim->stop_flag = 1;
                    log_message(sim, now, i + 1, "burned out");
                    // FIX: broadcast on global stop condition to wake all sleeping coder threads
                    pthread_cond_broadcast(&sim->stop_cond);
                }
                pthread_mutex_unlock(&sim->stop_mutex);
                // Wake all dongle waiters
                for (int j = 0; j < sim->num_coders; j++)
                {
                    pthread_mutex_lock(&sim->dongles[j].mutex);
                    pthread_cond_broadcast(&sim->dongles[j].cond);
                    pthread_mutex_unlock(&sim->dongles[j].mutex);
                }
                return NULL;
            }
        }

        int all_done = 1;
        for (int i = 0; i < sim->num_coders; i++)
        {
            if (sim->coders[i].compiles_done < sim->compiles_required)
            {
                all_done = 0;
                break;
            }
        }
        if (all_done)
        {
            pthread_mutex_lock(&sim->stop_mutex);
            sim->stop_flag = 1;
            pthread_cond_broadcast(&sim->stop_cond);   // FIX: wake all sleeping threads
            pthread_mutex_unlock(&sim->stop_mutex);
            for (int j = 0; j < sim->num_coders; j++)
            {
                pthread_mutex_lock(&sim->dongles[j].mutex);
                pthread_cond_broadcast(&sim->dongles[j].cond);
                pthread_mutex_unlock(&sim->dongles[j].mutex);
            }
            return NULL;
        }
        usleep(1000);
    }
    return NULL;
}

// ----------------------------------------------------------------------------
// Initialisation and cleanup
// ----------------------------------------------------------------------------

int parse_arguments(int argc, char **argv, t_sim *sim)
{
    if (argc != 9)
        return 0;
    sim->num_coders = atoi(argv[1]);
    sim->time_to_burnout = atoi(argv[2]);
    sim->time_to_compile = atoi(argv[3]);
    sim->time_to_debug = atoi(argv[4]);
    sim->time_to_refactor = atoi(argv[5]);
    sim->compiles_required = atoi(argv[6]);
    sim->dongle_cooldown = atoi(argv[7]);
    if (strcmp(argv[8], "fifo") == 0)
        sim->scheduler = 0;
    else if (strcmp(argv[8], "edf") == 0)
        sim->scheduler = 1;
    else
        return 0;
    if (sim->num_coders <= 0 || sim->time_to_burnout <= 0 || sim->time_to_compile <= 0 ||
        sim->time_to_debug <= 0 || sim->time_to_refactor <= 0 || sim->compiles_required <= 0 ||
        sim->dongle_cooldown < 0)
        return 0;
    return 1;
}

void init_simulation(t_sim *sim)
{
    sim->stop_flag = 0;
    pthread_mutex_init(&sim->stop_mutex, NULL);
    pthread_cond_init(&sim->stop_cond, NULL);   // FIX: initialise stop condition
    pthread_mutex_init(&sim->log_mutex, NULL);
    sim->sim_start_ms = get_current_ms();

    sim->coders = malloc(sim->num_coders * sizeof(t_coder));
    sim->dongles = malloc(sim->num_coders * sizeof(t_dongle));
    sim->coder_threads = malloc(sim->num_coders * sizeof(pthread_t));

    for (int i = 0; i < sim->num_coders; i++)
    {
        sim->dongles[i].id = i + 1;
        sim->dongles[i].in_use = 0;
        sim->dongles[i].cooldown_until = sim->sim_start_ms;
        pthread_mutex_init(&sim->dongles[i].mutex, NULL);
        pthread_cond_init(&sim->dongles[i].cond, NULL);
        if (sim->scheduler == 0)
            heap_init(&sim->dongles[i].wait_queue, compare_fifo);
        else
            heap_init(&sim->dongles[i].wait_queue, compare_edf);
    }

    for (int i = 0; i < sim->num_coders; i++)
    {
        sim->coders[i].id = i + 1;
        sim->coders[i].last_compile_start = sim->sim_start_ms;
        sim->coders[i].compiles_done = 0;
        if (i == 0)
        {
            sim->coders[i].left_dongle_id = sim->num_coders;
            sim->coders[i].right_dongle_id = 1;
        }
        else
        {
            sim->coders[i].left_dongle_id = i;
            sim->coders[i].right_dongle_id = i + 1;
        }
    }
}

void cleanup_simulation(t_sim *sim)
{
    for (int i = 0; i < sim->num_coders; i++)
    {
        pthread_mutex_destroy(&sim->dongles[i].mutex);
        pthread_cond_destroy(&sim->dongles[i].cond);
        heap_free(&sim->dongles[i].wait_queue);
    }
    pthread_mutex_destroy(&sim->stop_mutex);
    pthread_cond_destroy(&sim->stop_cond);   // FIX: destroy stop condition
    pthread_mutex_destroy(&sim->log_mutex);
    free(sim->coders);
    free(sim->dongles);
    free(sim->coder_threads);
}

// ----------------------------------------------------------------------------
// Main
// ----------------------------------------------------------------------------

int main(int argc, char **argv)
{
    t_sim sim;
    if (!parse_arguments(argc, argv, &sim))
    {
        fprintf(stderr, "Usage error: %s number_of_coders time_to_burnout time_to_compile time_to_debug time_to_refactor number_of_compiles_required dongle_cooldown {fifo|edf}\n", argv[0]);
        return 1;
    }

    init_simulation(&sim);

    for (int i = 0; i < sim.num_coders; i++)
    {
        t_thread_arg *arg = malloc(sizeof(t_thread_arg));
        arg->sim = &sim;
        arg->coder_id = i + 1;
        pthread_create(&sim.coder_threads[i], NULL, coder_routine, arg);
    }

    pthread_create(&sim.monitor_thread, NULL, monitor_routine, &sim);

    for (int i = 0; i < sim.num_coders; i++)
        pthread_join(sim.coder_threads[i], NULL);
    pthread_join(sim.monitor_thread, NULL);

    cleanup_simulation(&sim);
    return 0;
}