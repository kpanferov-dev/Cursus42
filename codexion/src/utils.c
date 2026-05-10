#include "codexion.h"
#include <stdlib.h>
#include <unistd.h>
#include <stdio.h>

long long	get_ms(struct timeval start)
{
	struct timeval	now;
	long long		sec, usec;

	gettimeofday(&now, NULL);
	sec = now.tv_sec - start.tv_sec;
	usec = now.tv_usec - start.tv_usec;
	return (sec * 1000 + usec / 1000);
}

void	log_msg(t_sim *sim, int id, const char *str, long long ts)
{
	pthread_mutex_lock(&sim->log);
	printf("%lld %d %s\n", ts, id, str);
	pthread_mutex_unlock(&sim->log);
}

void	sim_sleep_ms(t_sim *sim, int ms)
{
	long long	goal;
	int			step;

	goal = get_ms(sim->start) + ms;
	while (sim_running(sim))
	{
		if (get_ms(sim->start) >= goal)
			break ;
		step = (goal - get_ms(sim->start) > 10) ? 10 : 1;
		usleep(step * 1000);
	}
}