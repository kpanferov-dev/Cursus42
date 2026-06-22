/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   codexion_dongle.c                                  :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: kpanfero <kpanfero@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2024/01/01 00:00:00 by marvin            #+#    #+#             */
/*   Updated: 2026/06/20 16:40:03 by kpanfero         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

/*
** Wait until this coder is allowed to use the dongle.
**
** Conditions to acquire the dongle:
** - this coder is at the top of the priority queue
** - dongle is not currently in use
** - cooldown time has passed
**
** If not ready → sleep using condition variable (efficient wait)
*/
static int	dongle_wait_turn(t_sim *sim, t_dongle *d, int id)
{
	t_heap_node		*top;
	long long		now;
	long long		wait_until;
	struct timespec	ts;

	while (!sim->stop_flag)
	{
		top = heap_peek(&d->wait_queue);
		if (top && top->coder_id == id && d->in_use == 0
			&& get_current_ms() >= d->cooldown_until)
			return (1);
		now = get_current_ms();
		wait_until = d->cooldown_until;
		if (wait_until <= now)
			wait_until = now + 10;
		ts.tv_sec = wait_until / 1000;
		ts.tv_nsec = (wait_until % 1000) * 1000000;
		pthread_cond_timedwait(&d->cond, &d->mutex, &ts);
	}
	return (0);
}

/*
** Try to acquire a dongle for a coder.
**
** Steps:
** 1. Add coder to priority queue (wait list)
** 2. Wait until it's their turn
** 3. If allowed → take dongle
** 4. If not → remove from queue and fail
*/
int	dongle_acquire(t_sim *sim, t_dongle *d, int id, long long key)
{
	t_heap_node	node;
	int			ready;

	pthread_mutex_lock(&d->mutex);
	node.coder_id = id;
	node.key = key;
	heap_push(&d->wait_queue, node);
	ready = dongle_wait_turn(sim, d, id);
	if (ready)
	{
		heap_pop(&d->wait_queue);
		d->in_use = 1;
		pthread_mutex_unlock(&d->mutex);
		return (0);
	}
	heap_remove_coder(&d->wait_queue, id);
	pthread_mutex_unlock(&d->mutex);
	return (-1);
}

/*
** Release a dongle after use.
**
** Steps:
** - mark dongle as free
** - set cooldown (prevents immediate reuse)
** - wake all waiting coders
*/
void	dongle_release(t_sim *sim, t_dongle *d)
{
	pthread_mutex_lock(&d->mutex);
	d->in_use = 0;
	d->cooldown_until = get_current_ms() + sim->dongle_cooldown;
	pthread_cond_broadcast(&d->cond);
	pthread_mutex_unlock(&d->mutex);
}
