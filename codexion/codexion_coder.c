/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   codexion_coder.c                                   :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: kpanfero <kpanfero@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2024/01/01 00:00:00 by marvin            #+#    #+#             */
/*   Updated: 2026/06/20 16:49:57 by kpanfero         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

/*
** Assigns the two dongles a coder needs.
**
** Also enforces a consistent order (first < second)
** to reduce deadlock risk when acquiring resources.
*/
static void	coder_set_dongles(t_sim *sim, t_coder *coder,
				t_dongle **first, t_dongle **second)
{
	t_dongle	*left;
	t_dongle	*right;

	left = &sim->dongles[coder->left_dongle_id - 1];
	right = &sim->dongles[coder->right_dongle_id - 1];
	if (coder->left_dongle_id < coder->right_dongle_id)
	{
		*first = left;
		*second = right;
	}
	else
	{
		*first = right;
		*second = left;
	}
}

/*
** Tries to acquire both dongles needed for compilation.
**
** Steps:
** 1. Compute scheduling key (FIFO or EDF)
** 2. Acquire first dongle
** 3. Acquire second dongle
** 4. If second fails → release first (avoid deadlock / partial hold)
*/
static int	coder_take_dongles(t_sim *sim, t_dongle *first,
				t_dongle *second, int id)
{
	long long	key;

	if (sim->scheduler == 0)
		key = get_current_ms();
	else
		key = sim->coders[id - 1].last_compile_start + sim->time_to_burnout;
	if (dongle_acquire(sim, first, id, key) == -1)
		return (-1);
	log_message(sim, get_current_ms(), id, "has taken a dongle");
	if (dongle_acquire(sim, second, id, key) == -1)
	{
		dongle_release(sim, first);
		return (-1);
	}
	log_message(sim, get_current_ms(), id, "has taken a dongle");
	return (0);
}

/*
** Handles the compilation phase of a coder.
**
** Flow:
** 1. Take both dongles
** 2. Start compiling
** 3. Sleep (simulate compile time)
** 4. Release dongles
** 5. Update compile counter
*/
static int	coder_compile(t_sim *sim, t_coder *coder, t_dongle *first,
				t_dongle *second)
{
	int	id;

	id = coder->id;
	if (coder_take_dongles(sim, first, second, id) == -1)
		return (-1);
	coder->last_compile_start = get_current_ms();
	log_message(sim, coder->last_compile_start, id, "is compiling");
	if (interruptible_sleep(sim, sim->time_to_compile))
	{
		dongle_release(sim, first);
		dongle_release(sim, second);
		return (-1);
	}
	dongle_release(sim, first);
	dongle_release(sim, second);
	coder->compiles_done++;
	return (0);
}

/*
** Simulates non-critical work phases:
** - debugging
** - refactoring
**
** These do NOT require dongles.
*/
static int	coder_think(t_sim *sim, int id)
{
	if (sim->stop_flag)
		return (-1);
	log_message(sim, get_current_ms(), id, "is debugging");
	if (interruptible_sleep(sim, sim->time_to_debug))
		return (-1);
	if (sim->stop_flag)
		return (-1);
	log_message(sim, get_current_ms(), id, "is refactoring");
	if (interruptible_sleep(sim, sim->time_to_refactor))
		return (-1);
	return (0);
}

/*
** MAIN LOOP OF EACH CODER THREAD
**
** Each coder repeatedly:
** 1. Takes dongles
** 2. Compiles
** 3. Thinks (debug + refactor)
**
** Stops when:
** - simulation ends
** - or required number of compiles is reached
*/
void	*coder_routine(void *arg)
{
	t_thread_arg	*thread_arg;
	t_sim			*sim;
	t_coder			*coder;
	t_dongle		*first;
	t_dongle		*second;

	thread_arg = (t_thread_arg *)arg;
	sim = thread_arg->sim;
	coder = &sim->coders[thread_arg->coder_id - 1];
	free(arg);
	coder_set_dongles(sim, coder, &first, &second);
	while (!sim->stop_flag && coder->compiles_done < sim->compiles_required)
	{
		if (coder_compile(sim, coder, first, second) == -1)
			break ;
		if (coder_think(sim, coder->id) == -1)
			break ;
	}
	return (NULL);
}
