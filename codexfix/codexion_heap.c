/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   codexion_heap.c                                    :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: kpanfero <kpanfero@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2024/01/01 00:00:00 by marvin            #+#    #+#             */
/*   Updated: 2026/06/15 12:40:32 by kpanfero         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

void	heap_swap(t_heap_node *a, t_heap_node *b)
{
	t_heap_node	tmp;

	tmp = *a;
	*a = *b;
	*b = tmp;
}

int	heapify_up(t_heap *h, int idx)
{
	int	parent;

	while (idx > 0)
	{
		parent = (idx - 1) / 2;
		if (h->cmp(h->arr[idx], h->arr[parent]))
		{
			heap_swap(&h->arr[idx], &h->arr[parent]);
			idx = parent;
		}
		else
			break ;
	}
	return (idx);
}

void	heapify_down(t_heap *h, int idx)
{
	int	left;
	int	right;
	int	largest;

	while (1)
	{
		left = idx * 2 + 1;
		right = idx * 2 + 2;
		largest = idx;
		if (left < h->size && h->cmp(h->arr[left], h->arr[largest]))
			largest = left;
		if (right < h->size && h->cmp(h->arr[right], h->arr[largest]))
			largest = right;
		if (largest != idx)
		{
			heap_swap(&h->arr[idx], &h->arr[largest]);
			idx = largest;
		}
		else
			break ;
	}
}

void	heap_push(t_heap *h, t_heap_node node)
{
	t_heap_node	*new_arr;
	int			new_cap;
	int			idx;

	if (h->size >= h->capacity)
	{
		if (h->capacity == 0)
			new_cap = 4;
		else
			new_cap = h->capacity * 2;
		new_arr = realloc(h->arr, new_cap * sizeof(t_heap_node));
		if (!new_arr)
			return ;
		h->arr = new_arr;
		h->capacity = new_cap;
	}
	idx = h->size++;
	h->arr[idx] = node;
	heapify_up(h, idx);
}

t_heap_node	heap_pop(t_heap *h)
{
	t_heap_node	top;

	top = h->arr[0];
	h->arr[0] = h->arr[--h->size];
	heapify_down(h, 0);
	return (top);
}
