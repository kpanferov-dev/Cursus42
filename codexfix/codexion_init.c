/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   codexion_init.c                                    :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: marvin <marvin@student.42.fr>              +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2024/01/01 00:00:00 by marvin            #+#    #+#             */
/*   Updated: 2024/01/01 00:00:00 by marvin           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

static int	args_are_valid(t_sim *sim)
{
	if (sim->num_coders <= 0 || sim->time_to_burnout <= 0)
		return (0);
	if (sim->time_to_compile <= 0 || sim->time_to_debug <= 0)
		return (0);
	if (sim->time_to_refactor <= 0 || sim->compiles_required <= 0)
		return (0);
	if (sim->dongle_cooldown < 0)
		return (0);
	return (1);
}

int	parse_arguments(int argc, char **argv, t_sim *sim)
{
	if (argc != 9)
		return (0);
	sim->num_coders = atoi(argv[1]);
	sim->time_to_burnout = atoi(argv[2]);
	sim->time_to_compile = atoi(argv[3]);
	sim->time_to_debug = atoi(argv[4]);
	sim->time_to_refactor = atoi(argv[5]);
	sim->compiles_required = atoi(argv[6]);
	sim->dongle_cooldown = atoi(argv[7]);
	if (strcmp(argv[8], "fifo") == 0)
		sim->scheduler = 0;
	else if (strcmp(argv[8], "edf") == 0)
		sim->scheduler = 1;
	else
		return (0);
	return (args_are_valid(sim));
}

static void	init_dongles(t_sim *sim)
{
	int	i;

	i = 0;
	while (i < sim->num_coders)
	{
		sim->dongles[i].id = i + 1;
		sim->dongles[i].in_use = 0;
		sim->dongles[i].cooldown_until = sim->sim_start_ms;
		pthread_mutex_init(&sim->dongles[i].mutex, NULL);
		pthread_cond_init(&sim->dongles[i].cond, NULL);
		if (sim->scheduler == 0)
			heap_init(&sim->dongles[i].wait_queue, compare_fifo);
		else
			heap_init(&sim->dongles[i].wait_queue, compare_edf);
		i++;
	}
}

static void	init_coders(t_sim *sim)
{
	int	i;

	i = 0;
	while (i < sim->num_coders)
	{
		sim->coders[i].id = i + 1;
		sim->coders[i].last_compile_start = sim->sim_start_ms;
		sim->coders[i].compiles_done = 0;
		if (i == 0)
		{
			sim->coders[i].left_dongle_id = sim->num_coders;
			sim->coders[i].right_dongle_id = 1;
		}
		else
		{
			sim->coders[i].left_dongle_id = i;
			sim->coders[i].right_dongle_id = i + 1;
		}
		i++;
	}
}

void	init_simulation(t_sim *sim)
{
	sim->stop_flag = 0;
	pthread_mutex_init(&sim->stop_mutex, NULL);
	pthread_cond_init(&sim->stop_cond, NULL);
	pthread_mutex_init(&sim->log_mutex, NULL);
	sim->sim_start_ms = get_current_ms();
	sim->coders = malloc(sim->num_coders * sizeof(t_coder));
	sim->dongles = malloc(sim->num_coders * sizeof(t_dongle));
	sim->coder_threads = malloc(sim->num_coders * sizeof(pthread_t));
	init_dongles(sim);
	init_coders(sim);
}
