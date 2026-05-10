#ifndef CODEXION_H
# define CODEXION_H

# include <pthread.h>
# include <sys/time.h>

/* ---------- structures ---------- */

typedef enum e_sched { FIFO, EDF } t_sched;

typedef struct s_req
{
	int	coder_id;
	int	priority;
}	t_req;

/* priority queue (min-heap) inside each dongle */
typedef struct s_pqueue
{
	t_req	*data;
	int		capacity;
	int		size;
}	t_pqueue;

typedef struct s_dongle
{
	pthread_mutex_t	mutex;
	pthread_cond_t	cond;
	int				held_by;			/* 0 if free */
	long long		cooldown_end;		/* timestamp (ms) */
	t_pqueue		wait;
}	t_dongle;

typedef struct s_coder
{
	int				id;
	pthread_t		thread;
	int				left_d;				/* index of left dongle */
	int				right_d;			/* index of right dongle */
	int				compiles;			/* how many times compiled */
	int				reached;			/* already counted for global target */
	long long		last_compile_start;	/* timestamp */
	int				burned_out;
	pthread_mutex_t	mutex;
	struct s_sim	*sim;				/* direct pointer, no hack */
}	t_coder;

/* global simulation state */
typedef struct s_sim
{
	int				n;					/* number of coders */
	int				ttb;				/* time_to_burnout (ms) */
	int				ttc;				/* time_to_compile (ms) */
	int				ttd;				/* time_to_debug (ms) */
	int				ttr;				/* time_to_refactor (ms) */
	int				req_comp;			/* number_of_compiles_required */
	int				dcd;				/* dongle_cooldown (ms) */
	t_sched			sched;
	struct timeval	start;
	t_dongle		**dongles;
	t_coder			*coders;
	pthread_mutex_t	log;
	pthread_mutex_t	state;
	int				running;
	int				all_done;			/* all coders reached req_comp */
	int				target_cnt;			/* how many coders already counted */
	pthread_t		monitor;
	int				req_counter;		/* for strict FIFO order */
}	t_sim;

/* ---------- prototypes ---------- */

/* parse.c */
int		parse_args(int ac, char **av, t_sim *sim);

/* sim.c */
void	sim_init(t_sim *sim);
void	sim_destroy(t_sim *sim);
int		sim_running(t_sim *sim);
void	sim_stop(t_sim *sim);
void	sim_target_increment(t_sim *sim, t_coder *coder);

/* coder.c */
void	*coder_routine(void *arg);

/* dongle.c */
void	dongle_init(t_dongle *d, int n);
void	dongle_destroy(t_dongle *d);
int		dongle_acquire(t_sim *sim, t_coder *coder, int d_idx);
void	dongle_release(t_sim *sim, int d_idx, long long now);
void	dongle_wake_all(t_sim *sim);

/* monitor.c */
void	*monitor_routine(void *arg);

/* priority_queue.c */
void	pq_init(t_pqueue *pq, int cap);
void	pq_destroy(t_pqueue *pq);
void	pq_push(t_pqueue *pq, int coder_id, int prio, t_sched sched);
t_req	pq_pop(t_pqueue *pq);
int		pq_is_empty(t_pqueue *pq);
void	pq_remove_coder(t_pqueue *pq, int coder_id);

/* utils.c */
long long	get_ms(struct timeval start);
void		log_msg(t_sim *sim, int id, const char *str, long long ts);
void		sim_sleep_ms(t_sim *sim, int ms);

#endif