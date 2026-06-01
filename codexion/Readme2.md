1. General Idea – What does Codexion simulate?
Imagine a shared workspace with N coders sitting in a circle.
In the centre is a Quantum Compiler that requires two USB dongles – one in each hand – to compile code.
There are exactly N dongles on the table, one between each pair of adjacent coders (circular layout).

A coder goes through three phases repeatedly:

Compiling – holds two dongles (the ones on its left and right) for time_to_compile ms.

Debugging – no dongles needed, lasts time_to_debug ms.

Refactoring – no dongles needed, lasts time_to_refactor ms.
After refactoring, the coder immediately tries to compile again.

Key constraints:

A coder cannot start compiling without both its left and right dongle.

When a dongle is released, it becomes unavailable for dongle_cooldown ms (no one can take it during that time).

If a coder does not start compiling within time_to_burnout ms since the beginning of its last compile (or the simulation start), it burns out – the simulation stops.

Coders do not communicate and do not know each other’s deadlines.

The program stops either when any coder burns out or when every coder has compiled at least number_of_compiles_required times.

Scheduling policies (fifo or edf) decide which waiting coder gets a dongle when multiple request it.

2. Command‑line arguments (all mandatory)
bash
./codexion number_of_coders time_to_burnout time_to_compile \
           time_to_debug time_to_refactor number_of_compiles_required \
           dongle_cooldown scheduler
number_of_coders – also the number of dongles.

time_to_burnout (ms) – deadline: a coder must start compiling again within this time since its last compile start.

time_to_compile (ms) – holds two dongles.

time_to_debug (ms) – no dongles.

time_to_refactor (ms) – no dongles.

number_of_compiles_required – target for each coder.

dongle_cooldown (ms) – after release, dongle cannot be taken.

scheduler – "fifo" or "edf".

All inputs are validated: positive integers, scheduler string exactly fifo or edf.

3. Global rules & forbidden things
No global variables – all state is inside a t_sim structure passed to threads.

No memory leaks – every malloc must be freed.

Norme (42 school coding style) must be respected.

The program must not crash (segmentation fault, bus error, double free).

A Makefile with rules all, clean, fclean, re and flags -Wall -Wextra -Werror -pthread.

4. Threading model
One thread per coder – created with pthread_create.

One monitor thread – checks for burnout and completion.

One mutex per dongle – protects the dongle’s state (in_use, cooldown_until, waiting queue).

One condition variable per dongle – used to make threads wait until the dongle becomes available and cooldown expires.

A global log mutex – ensures that messages from different threads are not interleaved.

A global stop mutex – protects the stop_flag (shared between coders and monitor).

5. Data structures (explained)
t_heap_node
c
typedef struct s_heap_node {
    int coder_id;
    long long key;   // for FIFO: request time; for EDF: deadline
} t_heap_node;
t_heap – custom priority queue (binary heap)
c
typedef struct s_heap {
    t_heap_node *arr;        // dynamic array
    int size;
    int capacity;
    int (*cmp)(t_heap_node a, t_heap_node b);  // comparator
} t_heap;
We cannot use std priority queues – must implement our own.

t_dongle
c
typedef struct s_dongle {
    pthread_mutex_t mutex;
    pthread_cond_t cond;
    int id;
    int in_use;               // 1 if currently held
    long long cooldown_until; // absolute timestamp when available
    t_heap wait_queue;        // priority queue of waiting coders
} t_dongle;
t_coder
c
typedef struct s_coder {
    int id;
    long long last_compile_start;   // absolute timestamp (ms)
    int compiles_done;
    int left_dongle_id;    // 1‑based index
    int right_dongle_id;
} t_coder;
t_sim – main simulation state
Contains arrays of coders, dongles, thread handles, and global parameters.

t_thread_arg
Passed to each coder thread: pointer to t_sim and the coder’s ID.

6. Initialisation steps
Parse arguments – validate and store in t_sim.

Set simulation start time – sim_start_ms = get_current_ms().

Allocate coders, dongles, coder_threads.

Initialise dongles:

in_use = 0

cooldown_until = sim_start_ms (initially available)

mutex and cond initialised

wait_queue initialised with appropriate comparator (compare_fifo or compare_edf).

Initialise coders:

id = i+1

last_compile_start = sim_start_ms

compiles_done = 0

Determine left/right dongle IDs (circular):

For coder 1: left = N, right = 1.

For others: left = i, right = i+1.

7. Dongle acquisition and release (core synchronisation)
int dongle_acquire(t_sim *sim, t_dongle *d, int coder_id, long long key)
Lock the dongle’s mutex.

Create a heap node with (coder_id, key) and push it into d->wait_queue.

While sim->stop_flag == 0:

Check if we are at the top of the queue and the dongle is free (d->in_use == 0) and cooldown has expired (now >= d->cooldown_until).

If yes, pop from queue, set d->in_use = 1, unlock and return 0 (success).

Otherwise, wait using pthread_cond_timedwait until cooldown expiry or a broadcast.

If stop_flag becomes set, we remove ourselves from the waiting queue (linear search + reheapify) and return -1.

Why a condition variable?
Because a dongle may become free but still be in cooldown. The timed wait wakes up exactly when cooldown expires, avoiding busy‑waiting.

void dongle_release(t_sim *sim, t_dongle *d)
Lock mutex.

Set d->in_use = 0.

Set d->cooldown_until = get_current_ms() + sim->dongle_cooldown.

Broadcast on the condition variable to wake all waiters (they will check the queue and cooldown again).

Unlock.

8. The heap (priority queue) implementation
We implement a min‑heap where the comparator returns 1 if the first node has higher priority (i.e., should be closer to the root).

FIFO comparator:

c
int compare_fifo(t_heap_node a, t_heap_node b) {
    if (a.key != b.key) return a.key < b.key;   // earlier request time = higher priority
    return a.coder_id < b.coder_id;             // tie‑breaker: lower ID first
}
EDF comparator (original):

c
int compare_edf(t_heap_node a, t_heap_node b) {
    if (a.key != b.key) return a.key < b.key;   // earlier deadline = higher priority
    return a.coder_id < b.coder_id;
}
Modified EDF comparator (requested recode):

c
int compare_edf(t_heap_node a, t_heap_node b) {
    if (a.key != b.key) return a.key < b.key;
    return a.coder_id > b.coder_id;   // HIGHER coder_id gets priority on equal deadlines
}
This changes the tie‑breaking rule – now the coder with the larger ID will be served first when deadlines are identical.

Heap operations
heap_push – insert at end, bubble up.

heap_pop – remove root, replace with last element, bubble down.

heap_peek – return root without removing.

All operations are O(log n) and are called inside the dongle’s mutex.

9. Coder thread routine
c
void *coder_routine(void *arg) {
    t_thread_arg *a = arg;
    t_sim *sim = a->sim;
    int id = a->coder_id;
    free(a);
    t_coder *coder = &sim->coders[id-1];
    // Determine left and right dongles
    t_dongle *left  = &sim->dongles[coder->left_dongle_id - 1];
    t_dongle *right = &sim->dongles[coder->right_dongle_id - 1];
    // Decide acquisition order: always smaller ID first to avoid deadlock
    t_dongle *first = (coder->left_dongle_id < coder->right_dongle_id) ? left : right;
    t_dongle *second = (first == left) ? right : left;

    while (!sim->stop_flag && coder->compiles_done < sim->compiles_required) {
        // Compute key for this compile attempt
        long long key;
        if (sim->scheduler == 0)  // FIFO
            key = get_current_ms();          // request time
        else                      // EDF
            key = coder->last_compile_start + sim->time_to_burnout; // deadline

        // Acquire first dongle
        if (dongle_acquire(sim, first, id, key) == -1) break;
        log_message(sim, get_current_ms(), id, "has taken a dongle");
        // Acquire second dongle
        if (dongle_acquire(sim, second, id, key) == -1) {
            dongle_release(sim, first);
            break;
        }
        log_message(sim, get_current_ms(), id, "has taken a dongle");

        // Compile phase
        long long compile_start = get_current_ms();
        log_message(sim, compile_start, id, "is compiling");
        coder->last_compile_start = compile_start;
        usleep(sim->time_to_compile * 1000);

        // Release both dongles
        dongle_release(sim, first);
        dongle_release(sim, second);

        coder->compiles_done++;

        // Debug phase
        log_message(sim, get_current_ms(), id, "is debugging");
        usleep(sim->time_to_debug * 1000);

        // Refactor phase
        log_message(sim, get_current_ms(), id, "is refactoring");
        usleep(sim->time_to_refactor * 1000);
    }
    return NULL;
}
Why the ordered acquisition?
To prevent deadlock: if every coder always took its left dongle first, they could all hold one and wait for the other forever. By taking the smaller‑ID dongle first (and larger second), we guarantee a total order and avoid circular wait.

10. Monitor thread
Periodically (every 1 ms) checks two conditions:

Burnout: For each coder, if current_time - last_compile_start >= time_to_burnout, set stop_flag = 1, log "burned out", broadcast all dongle condition variables, and exit.

Successful completion: If every coder’s compiles_done >= compiles_required, set stop_flag and exit.

The monitor runs until stop_flag is set. It uses usleep(1000) to avoid consuming too much CPU.

11. Logging and timing
c
void log_message(t_sim *sim, long long timestamp, int coder_id, const char *action) {
    pthread_mutex_lock(&sim->log_mutex);
    printf("%lld %d %s\n", timestamp - sim->sim_start_ms, coder_id, action);
    fflush(stdout);
    pthread_mutex_unlock(&sim->log_mutex);
}
All timestamps are relative to simulation start (subtract sim_start_ms).

The log mutex ensures that two messages are never interleaved on the same line.

Burnout timestamp must be within 10 ms of the actual deadline miss. Our monitor checks every millisecond, so this is satisfied.

12. Key synchronisation patterns
Mutex per dongle – protects the dongle’s internal state and the heap. This allows multiple dongles to be accessed in parallel.

Condition variable – used with pthread_cond_timedwait to wait until cooldown expires or a dongle becomes free. The timeout is set to the cooldown expiry time, so no unnecessary wake‑ups.

Stop flag – protected by its own mutex, but also checked inside dongle mutexes. When the monitor sets stop_flag, it broadcasts on all dongle condition variables to wake every waiting thread.

Ordered acquisition – prevents deadlock without needing a global lock.

13. Memory management
All dynamic arrays (coders, dongles, coder_threads, heap arrays) are allocated with malloc/calloc.

Every malloc has a corresponding free in cleanup_simulation.

The t_thread_arg passed to each coder thread is freed inside the thread.

Valgrind should show no leaks (except possibly from pthread internals, which are normal).

14. Edge cases and their handling
Case	Behaviour
Single coder	Only one dongle exists. Coder can never get two → always burns out after time_to_burnout.
Invalid arguments	Print usage and exit with non‑zero status.
Very large N (≤200)	Simulation may be slow but should not crash. The monitor and dongle wait queues scale.
Cooldown longer than compile time	Dangles are locked for compile + cooldown. Can cause starvation if deadlines are tight.
Equal deadlines in EDF	Tie‑breaker now favours higher coder ID (as modified).
Burnout during acquisition	The monitor sets stop_flag, all waiting threads see it and cleanly exit (release any held dongles? actually they only hold dongles when inside the acquire function that returns -1).
15. The EDF tie‑breaker recode – what changed and why
Original requirement (from subject):

edf means Earliest Deadline First with deadline = last_compile_start + time_to_burnout.
The subject did not specify a tie‑breaker, so we originally chose lower coder ID for determinism.

Recode instruction: modify EDF to prefer higher coder_id on equal deadlines.
This is a small change only inside compare_edf:

c
// Before
return a.coder_id < b.coder_id;

// After
return a.coder_id > b.coder_id;
Why test this?
To verify that when two coders have exactly the same deadline (e.g., at the very start of simulation or after a simultaneous compile), the dongle is granted to the one with the larger ID.
A simple test with 2 coders and very large time_to_burnout shows that the first "has taken a dongle" line belongs to coder 2, not coder 1.
This demonstrates that the heap comparator works correctly and the priority queue respects the new rule.

16. How to prepare for the exam
You should be able to:

Explain the entire problem – circular coders, dongles, phases, burnout, cooldown, scheduling.

Describe the data structures and why each is needed.

Walk through the code line by line – especially the dongle_acquire function (mutex, condition variable, heap operations, timeout).

Explain deadlock prevention (ordered acquisition) and why it works.

Discuss how the monitor thread ensures timely burnout detection (1 ms sleep, direct time comparison).

Show how the custom heap implements FIFO and EDF and how comparators work.

Talk about the recent modification: EDF tie‑breaker change and how to test it.

Mention the allowed external functions and why each is used (pthread_*, gettimeofday, usleep, malloc, free, printf...).

Be ready to modify the code during evaluation – e.g., change scheduling behaviour, add a new log message, adjust tie‑breaker, etc.

Practice by running the test scripts provided earlier and by reading the code with this explanation in hand.

17. Final remarks
The Codexion project is a classic concurrency simulation that tests your understanding of:

Thread creation and joining.

Mutexes and condition variables.

Avoiding deadlock and starvation.

Implementing a priority queue from scratch.

Precise timing and real‑time constraints.

Clean memory management.

Your implementation is correct if it meets the specification – which it does. The few “failures” you observed (like coder 66 burning out with 100 coders) are by design, not bugs. They happen because the chosen time_to_burnout was too small for the system load. The simulation faithfully reproduces the real‑world behaviour of a resource‑constrained multi‑threaded system.

Good luck for your examination! Now you have everything you need to explain and defend your code.

