/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   codexion.h                                         :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: marvin <marvin@student.42.fr>              +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2024/01/01 00:00:00 by marvin            #+#    #+#             */
/*   Updated: 2024/01/01 00:00:00 by marvin           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef CODEXION_H
# define CODEXION_H

# include <pthread.h>
# include <stdio.h>
# include <stdlib.h>
# include <string.h>
# include <sys/time.h>
# include <unistd.h>

typedef struct s_heap_node
{
	int			coder_id;
	long long	key;
}	t_heap_node;

typedef struct s_heap
{
	t_heap_node	*arr;
	int			size;
	int			capacity;
	int			(*cmp)(t_heap_node, t_heap_node);
}	t_heap;

typedef struct s_dongle
{
	int				id;
	int				in_use;
	long long		cooldown_until;
	pthread_mutex_t	mutex;
	pthread_cond_t	cond;
	t_heap			wait_queue;
}	t_dongle;

typedef struct s_coder
{
	int			id;
	long long	last_compile_start;
	int			compiles_done;
	int			left_dongle_id;
	int			right_dongle_id;
}	t_coder;

typedef struct s_sim
{
	int				num_coders;
	int				time_to_burnout;
	int				time_to_compile;
	int				time_to_debug;
	int				time_to_refactor;
	int				compiles_required;
	int				dongle_cooldown;
	int				scheduler;
	int				stop_flag;
	long long		sim_start_ms;
	pthread_mutex_t	stop_mutex;
	pthread_cond_t	stop_cond;
	pthread_mutex_t	log_mutex;
	t_coder			*coders;
	t_dongle		*dongles;
	pthread_t		*coder_threads;
	pthread_t		monitor_thread;
}	t_sim;

typedef struct s_thread_arg
{
	t_sim	*sim;
	int		coder_id;
}	t_thread_arg;

long long	get_current_ms(void);
void		log_message(t_sim *sim, long long ms, int id, const char *action);
int			interruptible_sleep(t_sim *sim, int ms);
int			compare_fifo(t_heap_node a, t_heap_node b);
int			compare_edf(t_heap_node a, t_heap_node b);
void		heap_swap(t_heap_node *a, t_heap_node *b);
int			heapify_up(t_heap *h, int idx);
void		heapify_down(t_heap *h, int idx);
void		heap_push(t_heap *h, t_heap_node node);
t_heap_node	heap_pop(t_heap *h);
void		heap_init(t_heap *h, int (*cmp)(t_heap_node, t_heap_node));
t_heap_node	*heap_peek(t_heap *h);
int			heap_is_empty(t_heap *h);
void		heap_free(t_heap *h);
void		heap_remove_coder(t_heap *h, int coder_id);
int			dongle_acquire(t_sim *sim, t_dongle *d, int id, long long key);
void		dongle_release(t_sim *sim, t_dongle *d);
void		*coder_routine(void *arg);
void		*monitor_routine(void *arg);
int			parse_arguments(int argc, char **argv, t_sim *sim);
void		init_simulation(t_sim *sim);
void		cleanup_simulation(t_sim *sim);

#endif
