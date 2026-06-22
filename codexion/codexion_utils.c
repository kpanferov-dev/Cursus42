/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   codexion_utils.c                                   :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: kpanfero <kpanfero@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2024/01/01 00:00:00 by marvin            #+#    #+#             */
/*   Updated: 2026/06/20 16:09:29 by kpanfero         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

/*
** Returns the current time in milliseconds.
** Used to measure simulation timing (events, logs, delays).
*/
long long	get_current_ms(void)
{
	struct timeval	tv;

	gettimeofday(&tv, NULL);
	return ((long long)tv.tv_sec * 1000 + tv.tv_usec / 1000);
}

/*
** Thread-safe logging function.
**
** Prints a formatted message: [time] [id] [action]
** Protects output using a mutex to avoid mixed prints
** from multiple threads (coders).
**
** If simulation is stopped, ignores all logs except
** the final "burned out" state.
*/
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

/*
** Interruptible sleep function.
**
** Sleeps for 'ms' milliseconds BUT can wake early if:
** - simulation stops (stop_flag = 1)
** - stop_cond is signaled
**
** This avoids using busy-wait loops and allows clean exit
** of all threads when simulation ends.
**
** Returns:
** - 1 if simulation was stopped during sleep
** - 0 otherwise
*/
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

/*
** FIFO comparison function for heap scheduling.
**
** Priority rules:
** 1. Lower key wins (earlier arrival time)
** 2. If tie, lower coder_id wins
*/
int	compare_fifo(t_heap_node a, t_heap_node b)
{
	if (a.key != b.key)
		return (a.key < b.key);
	return (a.coder_id < b.coder_id);
}

/*
** EDF (Earliest Deadline First) comparison function.
**
** Priority rules:
** 1. Lower key wins (earliest deadline)
** 2. If tie, higher coder_id wins (reverse tie-break vs FIFO)
*/
int	compare_edf(t_heap_node a, t_heap_node b)
{
	if (a.key != b.key)
		return (a.key < b.key);
	return (a.coder_id > b.coder_id);
}
