/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   codexion_main.c                                    :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: kpanfero <kpanfero@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2024/01/01 00:00:00 by marvin            #+#    #+#             */
/*   Updated: 2026/06/20 16:22:24 by kpanfero         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

/*
** Starts the simulation by creating:
** - one thread per coder (coder_routine)
** - one monitor thread (monitor_routine)
**
** Then waits for all threads to finish using pthread_join.
*/
static void	run_simulation(t_sim *sim)
{
	int				i;
	t_thread_arg	*arg;

	i = 0;
	while (i < sim->num_coders)
	{
		arg = malloc(sizeof(t_thread_arg));
		arg->sim = sim;
		arg->coder_id = i + 1;
		pthread_create(&sim->coder_threads[i], NULL, coder_routine, arg);
		i++;
	}
	pthread_create(&sim->monitor_thread, NULL, monitor_routine, sim);
	i = 0;
	while (i < sim->num_coders)
	{
		pthread_join(sim->coder_threads[i], NULL);
		i++;
	}
	pthread_join(sim->monitor_thread, NULL);
}

/*
** Frees all resources used by the simulation:
** - destroys mutexes and condition variables
** - frees priority queues (heaps)
** - frees allocated memory
*/
void	cleanup_simulation(t_sim *sim)
{
	int	i;

	i = 0;
	while (i < sim->num_coders)
	{
		pthread_mutex_destroy(&sim->dongles[i].mutex);
		pthread_cond_destroy(&sim->dongles[i].cond);
		heap_free(&sim->dongles[i].wait_queue);
		i++;
	}
	pthread_mutex_destroy(&sim->stop_mutex);
	pthread_cond_destroy(&sim->stop_cond);
	pthread_mutex_destroy(&sim->log_mutex);
	free(sim->coders);
	free(sim->dongles);
	free(sim->coder_threads);
}

/*
** Entry point of the program.
**
** Flow:
** 1. Parse arguments
** 2. Initialize simulation structures
** 3. Run simulation (threads start here)
** 4. Cleanup all resources
*/
int	main(int argc, char **argv)
{
	t_sim	sim;

	if (!parse_arguments(argc, argv, &sim))
	{
		fprintf(stderr, "Usage error: %s number_of_coders "
			"time_to_burnout time_to_compile time_to_debug "
			"time_to_refactor number_of_compiles_required "
			"dongle_cooldown {fifo|edf}\n", argv[0]);
		return (1);
	}
	init_simulation(&sim);
	run_simulation(&sim);
	cleanup_simulation(&sim);
	return (0);
}
