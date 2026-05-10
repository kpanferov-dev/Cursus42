#include "codexion.h"
#include <stdlib.h>

void	dongle_init(t_dongle *d, int n)
{
	pthread_mutex_init(&d->mutex, NULL);
	pthread_cond_init(&d->cond, NULL);
	d->held_by = 0;
	d->cooldown_end = 0;
	pq_init(&d->wait, n);
}

void	dongle_destroy(t_dongle *d)
{
	pq_destroy(&d->wait);
	pthread_mutex_destroy(&d->mutex);
	pthread_cond_destroy(&d->cond);
}

int	dongle_acquire(t_sim *sim, t_coder *coder, int d_idx)
{
	t_dongle	*d;
	int			prio;

	d = sim->dongles[d_idx];
	pthread_mutex_lock(&d->mutex);
	pthread_mutex_lock(&coder->mutex);
	if (sim->sched == EDF)
		prio = coder->last_compile_start + sim->ttb;
	else
	{
		pthread_mutex_lock(&sim->state);
		prio = sim->req_counter++;         /* strict FIFO order */
		pthread_mutex_unlock(&sim->state);
	}
	pthread_mutex_unlock(&coder->mutex);
	pq_push(&d->wait, coder->id, prio, sim->sched);
	while (d->held_by != coder->id && sim_running(sim))
		pthread_cond_wait(&d->cond, &d->mutex);
	if (!sim_running(sim))
	{
		pq_remove_coder(&d->wait, coder->id);
		pthread_mutex_unlock(&d->mutex);
		return (-1);
	}
	pthread_mutex_lock(&coder->mutex);
	if (coder->burned_out)
	{
		d->held_by = 0;
		pthread_mutex_unlock(&coder->mutex);
		pthread_cond_broadcast(&d->cond);
		pthread_mutex_unlock(&d->mutex);
		return (-1);
	}
	pthread_mutex_unlock(&coder->mutex);
	pthread_mutex_unlock(&d->mutex);
	return (0);
}

void	dongle_release(t_sim *sim, int d_idx, long long now)
{
	t_dongle	*d;

	d = sim->dongles[d_idx];
	pthread_mutex_lock(&d->mutex);
	d->held_by = 0;
	d->cooldown_end = now + sim->dcd;
	pthread_mutex_unlock(&d->mutex);
}

void	dongle_wake_all(t_sim *sim)
{
	int	i;

	i = 0;
	while (i < sim->n)
	{
		pthread_mutex_lock(&sim->dongles[i]->mutex);
		pthread_cond_broadcast(&sim->dongles[i]->cond);
		pthread_mutex_unlock(&sim->dongles[i]->mutex);
		i++;
	}
}
