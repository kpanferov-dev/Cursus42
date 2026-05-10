#include "codexion.h"
#include <stdlib.h>
#include <string.h>

void	sim_init(t_sim *sim)
{
	int	i;

	gettimeofday(&sim->start, NULL);
	pthread_mutex_init(&sim->log, NULL);
	pthread_mutex_init(&sim->state, NULL);
	sim->running = 1;
	sim->all_done = 0;
	sim->target_cnt = 0;
	sim->req_counter = 0;               /* FIFO sequential id */
	sim->dongles = malloc(sizeof(t_dongle *) * sim->n);
	i = 0;
	while (i < sim->n)
	{
		sim->dongles[i] = malloc(sizeof(t_dongle));
		dongle_init(sim->dongles[i], sim->n);
		i++;
	}
	sim->coders = malloc(sizeof(t_coder) * sim->n);
	memset(sim->coders, 0, sizeof(t_coder) * sim->n);
	i = 0;
	while (i < sim->n)
	{
		sim->coders[i].id = i + 1;
		sim->coders[i].sim = sim;       /* safe, no overflow */
		pthread_mutex_init(&sim->coders[i].mutex, NULL);
		if (sim->n == 1)
		{
			sim->coders[i].left_d = 0;
			sim->coders[i].right_d = 0;
		}
		else
		{
			sim->coders[i].left_d = (i == 0) ? sim->n - 1 : i - 1;
			sim->coders[i].right_d = i;
		}
		i++;
	}
}

void	sim_destroy(t_sim *sim)
{
	int	i;

	i = 0;
	while (i < sim->n)
	{
		dongle_destroy(sim->dongles[i]);
		free(sim->dongles[i]);
		pthread_mutex_destroy(&sim->coders[i].mutex);
		i++;
	}
	free(sim->dongles);
	free(sim->coders);
	pthread_mutex_destroy(&sim->log);
	pthread_mutex_destroy(&sim->state);
}

int	sim_running(t_sim *sim)
{
	int	r;

	pthread_mutex_lock(&sim->state);
	r = sim->running;
	pthread_mutex_unlock(&sim->state);
	return (r);
}

void	sim_stop(t_sim *sim)
{
	pthread_mutex_lock(&sim->state);
	sim->running = 0;
	pthread_mutex_unlock(&sim->state);
	dongle_wake_all(sim);               /* wake all waiters so they exit */
}

void	sim_target_increment(t_sim *sim, t_coder *coder)
{
	pthread_mutex_lock(&coder->mutex);
	if (coder->compiles >= sim->req_comp && !coder->reached)
	{
		coder->reached = 1;
		pthread_mutex_unlock(&coder->mutex);
		pthread_mutex_lock(&sim->state);
		sim->target_cnt++;
		if (sim->target_cnt == sim->n)
			sim->all_done = 1;
		pthread_mutex_unlock(&sim->state);
		if (sim->all_done)
			sim_stop(sim);
	}
	else
		pthread_mutex_unlock(&coder->mutex);
}