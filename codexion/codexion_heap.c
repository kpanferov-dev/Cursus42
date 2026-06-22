/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   codexion_heap.c                                    :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: kpanfero <kpanfero@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2024/01/01 00:00:00 by marvin            #+#    #+#             */
/*   Updated: 2026/06/20 14:56:50 by kpanfero         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

/*
** Swap the contents of two heap nodes.
** Used when restoring the heap property.
*/
void	heap_swap(t_heap_node *a, t_heap_node *b)
{
	t_heap_node	tmp;

	tmp = *a;
	*a = *b;
	*b = tmp;
}

/*
** Move a node upward in the heap until the heap property is restored.
**
** Example:
**     Parent
**        5
**       /
**      10
**
** If cmp(10, 5) is true, swap them.
**
** Returns the final index of the node after bubbling up.
*/
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

/*
** Move a node downward until the heap property is restored.
**
** Used after removing the root.
*/
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

/*
** Insert a new node into the heap.
*/
void	heap_push(t_heap *h, t_heap_node node)
{
	int	idx;

	if (h->size >= h->capacity)
		return ;
	idx = h->size++;
	h->arr[idx] = node;
	heapify_up(h, idx);
}

/*
** Remove and return the root node.
**
** Root always contains:
** - maximum element in a max-heap
** - minimum element in a min-heap
*/
t_heap_node	heap_pop(t_heap *h)
{
	t_heap_node	top;

	top = h->arr[0];
	h->arr[0] = h->arr[--h->size];
	heapify_down(h, 0);
	return (top);
}
