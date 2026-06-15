/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   codexion_heap2.c                                   :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: kpanfero <kpanfero@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2024/01/01 00:00:00 by marvin            #+#    #+#             */
/*   Updated: 2026/06/15 12:40:34 by kpanfero         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

void	heap_init(t_heap *h, int (*cmp)(t_heap_node, t_heap_node))
{
	h->arr = NULL;
	h->size = 0;
	h->capacity = 0;
	h->cmp = cmp;
}

t_heap_node	*heap_peek(t_heap *h)
{
	if (h->size == 0)
		return (NULL);
	return (&h->arr[0]);
}

int	heap_is_empty(t_heap *h)
{
	return (h->size == 0);
}

void	heap_free(t_heap *h)
{
	free(h->arr);
	h->arr = NULL;
	h->size = 0;
	h->capacity = 0;
}

void	heap_remove_coder(t_heap *h, int coder_id)
{
	int	i;
	int	idx;

	i = 0;
	while (i < h->size)
	{
		if (h->arr[i].coder_id == coder_id)
		{
			h->arr[i] = h->arr[--h->size];
			idx = heapify_up(h, i);
			heapify_down(h, idx);
			break ;
		}
		i++;
	}
}
