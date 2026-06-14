/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   codexion_monitor.c                                 :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: marvin <marvin@student.42.fr>              +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2024/01/01 00:00:00 by marvin            #+#    #+#             */
/*   Updated: 2024/01/01 00:00:00 by marvin           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

static void	monitor_wake_dongles(t_sim *sim)
{
	int	j;

	j = 0;
	while (j < sim->num_coders)
	{
		pthread_mutex_lock(&sim->dongles[j].mutex);
		pthread_cond_broadcast(&sim->dongles[j].cond);
		pthread_mutex_unlock(&sim->dongles[j].mutex);
		j++;
	}
}

static int	monitor_check_burnout(t_sim *sim, long long now)
{
	int	i;

	i = 0;
	while (i < sim->num_coders)
	{
		if (now - sim->coders[i].last_compile_start >= sim->time_to_burnout)
		{
			pthread_mutex_lock(&sim->stop_mutex);
			if (!sim->stop_flag)
			{
				sim->stop_flag = 1;
				log_message(sim, now, i + 1, "burned out");
				pthread_cond_broadcast(&sim->stop_cond);
			}
			pthread_mutex_unlock(&sim->stop_mutex);
			monitor_wake_dongles(sim);
			return (1);
		}
		i++;
	}
	return (0);
}

static int	monitor_all_done(t_sim *sim)
{
	int	i;

	i = 0;
	while (i < sim->num_coders)
	{
		if (sim->coders[i].compiles_done < sim->compiles_required)
			return (0);
		i++;
	}
	pthread_mutex_lock(&sim->stop_mutex);
	sim->stop_flag = 1;
	pthread_cond_broadcast(&sim->stop_cond);
	pthread_mutex_unlock(&sim->stop_mutex);
	monitor_wake_dongles(sim);
	return (1);
}

void	*monitor_routine(void *arg)
{
	t_sim		*sim;
	long long	now;

	sim = (t_sim *)arg;
	while (!sim->stop_flag)
	{
		now = get_current_ms();
		if (monitor_check_burnout(sim, now))
			return (NULL);
		if (monitor_all_done(sim))
			return (NULL);
		usleep(1000);
	}
	return (NULL);
}
