#include "codexion.h"
#include <unistd.h>

static void	check_burnout(t_sim *sim, long long now)
{
	int	i;

	i = 0;
	while (i < sim->n)
	{
		pthread_mutex_lock(&sim->coders[i].mutex);
		if (!sim->coders[i].burned_out
			&& now - sim->coders[i].last_compile_start >= sim->ttb)
		{
			sim->coders[i].burned_out = 1;
			pthread_mutex_unlock(&sim->coders[i].mutex);
			log_msg(sim, sim->coders[i].id, "burned out",
				sim->coders[i].last_compile_start + sim->ttb);
			sim_stop(sim);                /* also wakes all dongles */
			return ;
		}
		pthread_mutex_unlock(&sim->coders[i].mutex);
		i++;
	}
}

static void	process_dongles(t_sim *sim, long long now)
{
	int			i;
	t_dongle	*d;

	i = 0;
	while (i < sim->n)
	{
		d = sim->dongles[i];
		pthread_mutex_lock(&d->mutex);
		if (d->held_by == 0 && now >= d->cooldown_end && !pq_is_empty(&d->wait))
		{
			t_req	req = pq_pop(&d->wait);
			d->held_by = req.coder_id;
			d->cooldown_end = 0;
			pthread_cond_broadcast(&d->cond);
		}
		pthread_mutex_unlock(&d->mutex);
		i++;
	}
}

void	*monitor_routine(void *arg)
{
	t_sim		*sim;
	long long	now;

	sim = (t_sim *)arg;
	while (sim_running(sim))
	{
		now = get_ms(sim->start);
		check_burnout(sim, now);
		if (!sim_running(sim))
			break ;
		process_dongles(sim, now);
		usleep(500);
	}
	return (NULL);
}