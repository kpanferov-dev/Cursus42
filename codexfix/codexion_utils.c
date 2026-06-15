/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   codexion_utils.c                                   :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: kpanfero <kpanfero@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2024/01/01 00:00:00 by marvin            #+#    #+#             */
/*   Updated: 2026/06/15 12:39:59 by kpanfero         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

long long	get_current_ms(void)
{
	struct timeval	tv;

	gettimeofday(&tv, NULL);
	return ((long long)tv.tv_sec * 1000 + tv.tv_usec / 1000);
}

void	log_message(t_sim *sim, long long ms, int id, const char *action)
{
	pthread_mutex_lock(&sim->log_mutex);
	if (sim->stop_flag && strcmp(action, "burned out") != 0)
	{
		pthread_mutex_unlock(&sim->log_mutex);
		return ;
	}
	printf("%lld %d %s\n", ms - sim->sim_start_ms, id, action);
	fflush(stdout);
	pthread_mutex_unlock(&sim->log_mutex);
}

int	interruptible_sleep(t_sim *sim, int ms)
{
	struct timespec	ts;
	long long		end;
	long long		remaining;
	int				stopped;

	pthread_mutex_lock(&sim->stop_mutex);
	end = get_current_ms() + ms;
	while (!sim->stop_flag && get_current_ms() < end)
	{
		remaining = end - get_current_ms();
		if (remaining <= 0)
			break ;
		ts.tv_sec = remaining / 1000;
		ts.tv_nsec = (remaining % 1000) * 1000000;
		pthread_cond_timedwait(&sim->stop_cond, &sim->stop_mutex, &ts);
	}
	stopped = sim->stop_flag;
	pthread_mutex_unlock(&sim->stop_mutex);
	return (stopped);
}

int	compare_fifo(t_heap_node a, t_heap_node b)
{
	if (a.key != b.key)
		return (a.key < b.key);
	return (a.coder_id < b.coder_id);
}

int	compare_edf(t_heap_node a, t_heap_node b)
{
	if (a.key != b.key)
		return (a.key < b.key);
	return (a.coder_id > b.coder_id);
}
