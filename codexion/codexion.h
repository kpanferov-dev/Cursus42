#ifndef CODEXION_H
#define CODEXION_H

#include <pthread.h>
#include <sys/time.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

typedef struct s_heap_node {
    int coder_id;
    long long key;
} t_heap_node;

typedef struct s_heap {
    t_heap_node *arr;
    int size;
    int capacity;
    int (*cmp)(t_heap_node a, t_heap_node b);
} t_heap;

typedef struct s_dongle {
    pthread_mutex_t mutex;
    pthread_cond_t cond;
    int id;
    int in_use;
    long long cooldown_until;
    t_heap wait_queue;
} t_dongle;

typedef struct s_coder {
    int id;
    long long last_compile_start;
    int compiles_done;
    int left_dongle_id;
    int right_dongle_id;
} t_coder;

typedef struct s_sim {
    int num_coders;
    int time_to_burnout;
    int time_to_compile;
    int time_to_debug;
    int time_to_refactor;
    int compiles_required;
    int dongle_cooldown;
    int scheduler;              // 0 = FIFO, 1 = EDF
    long long sim_start_ms;
    int stop_flag;
    pthread_mutex_t stop_mutex;
    pthread_mutex_t log_mutex;
    t_coder *coders;
    t_dongle *dongles;
    pthread_t *coder_threads;
    pthread_t monitor_thread;
} t_sim;

typedef struct s_thread_arg {
    t_sim *sim;
    int coder_id;
} t_thread_arg;

long long get_current_ms(void);
int parse_arguments(int argc, char **argv, t_sim *sim);
void init_simulation(t_sim *sim);
void cleanup_simulation(t_sim *sim);
void *coder_routine(void *arg);
void *monitor_routine(void *arg);
int dongle_acquire(t_sim *sim, t_dongle *d, int coder_id, long long key);
void dongle_release(t_sim *sim, t_dongle *d);
void log_message(t_sim *sim, long long timestamp, int coder_id, const char *action);
int compare_fifo(t_heap_node a, t_heap_node b);
int compare_edf(t_heap_node a, t_heap_node b);
void heap_init(t_heap *h, int (*cmp)(t_heap_node, t_heap_node));
void heap_push(t_heap *h, t_heap_node node);
t_heap_node heap_pop(t_heap *h);
t_heap_node *heap_peek(t_heap *h);
int heap_is_empty(t_heap *h);
void heap_free(t_heap *h);
void heap_swap(t_heap_node *a, t_heap_node *b);

#endif