#include "codexion.h"
#include <unistd.h>

static int	acquire_both(t_sim *sim, t_coder *coder)
{
	int	fst;
	int	snd;

	if (sim->n == 1)
		return (dongle_acquire(sim, coder, 0));
	fst = coder->left_d;
	snd = coder->right_d;
	if (fst > snd)
	{
		fst = coder->right_d;
		snd = coder->left_d;
	}
	if (dongle_acquire(sim, coder, fst) == -1)
		return (-1);
	log_msg(sim, coder->id, "has taken a dongle", get_ms(sim->start));
	if (dongle_acquire(sim, coder, snd) == -1)
	{
		dongle_release(sim, fst, get_ms(sim->start));
		return (-1);
	}
	log_msg(sim, coder->id, "has taken a dongle", get_ms(sim->start));
	return (0);
}

static void	release_both(t_sim *sim, t_coder *coder)
{
	long long	now;

	now = get_ms(sim->start);
	if (sim->n == 1)
		dongle_release(sim, 0, now);
	else
	{
		dongle_release(sim, coder->left_d, now);
		dongle_release(sim, coder->right_d, now);
	}
}

static void	do_compile(t_sim *sim, t_coder *coder)
{
	long long	now;

	now = get_ms(sim->start);
	pthread_mutex_lock(&coder->mutex);
	coder->last_compile_start = now;
	pthread_mutex_unlock(&coder->mutex);
	log_msg(sim, coder->id, "is compiling", now);
	sim_sleep_ms(sim, sim->ttc);
}

void	*coder_routine(void *arg)
{
	t_coder	*coder;
	t_sim	*sim;

	coder = (t_coder *)arg;
	sim = coder->sim;                       /* clean reference */
	coder->last_compile_start = get_ms(sim->start);
	while (sim_running(sim))
	{
		if (acquire_both(sim, coder) == -1)
			break ;
		if (!sim_running(sim))
		{
			release_both(sim, coder);
			break ;
		}
		do_compile(sim, coder);
		release_both(sim, coder);
		if (!sim_running(sim))
			break ;
		/* increment compile counter */
		pthread_mutex_lock(&coder->mutex);
		coder->compiles++;
		pthread_mutex_unlock(&coder->mutex);
		log_msg(sim, coder->id, "is debugging", get_ms(sim->start));
		sim_sleep_ms(sim, sim->ttd);
		if (!sim_running(sim))
			break ;
		log_msg(sim, coder->id, "is refactoring", get_ms(sim->start));
		sim_sleep_ms(sim, sim->ttr);
		sim_target_increment(sim, coder);
	}
	return (NULL);
}