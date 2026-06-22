/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   codexion_heap2.c                                   :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: kpanfero <kpanfero@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2024/01/01 00:00:00 by marvin            #+#    #+#             */
/*   Updated: 2026/06/20 15:11:23 by kpanfero         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

/*
** Initialize a heap.
**
** Parameters:
**   h        -> heap structure to initialize
**   cmp      -> comparison function defining priority
**   max_size -> maximum number of elements the heap can store
**
** Example:
**
**     heap_init(&heap, min_cost_cmp, 1000);
**
** This allocates memory for 1000 heap nodes and prepares
** the heap for use.
*/
void	heap_init(t_heap *h,
				int (*cmp)(t_heap_node, t_heap_node),
				int max_size)
{
	h->arr = malloc(max_size * sizeof(t_heap_node));
	if (!h->arr)
	{
		fprintf(stderr, "Error: heap_init malloc failed\n");
		exit(1);
	}
	h->size = 0;
	h->capacity = max_size;
	h->cmp = cmp;
}

/*
** Return the highest-priority element without removing it.
**
** For a min-heap:
**     returns smallest element
**
** For a max-heap:
**     returns largest element
**
** Since the root is always stored at index 0,
** this operation is O(1).
*/
t_heap_node	*heap_peek(t_heap *h)
{
	if (h->size == 0)
		return (NULL);
	return (&h->arr[0]);
}

/*
** Check whether heap contains any elements.
**
** Returns:
**
**     1 -> empty
**     0 -> not empty
**
** Equivalent to:
**
**     return (h->size == 0);
*/
int	heap_is_empty(t_heap *h)
{
	return (h->size == 0);
}

/*
** Release memory used by the heap.
**
** After this call the heap should not be used until
** heap_init() is called again.
*/
void	heap_free(t_heap *h)
{
	free(h->arr);
	h->arr = NULL;
	h->size = 0;
	h->capacity = 0;
}

/*
** Remove a specific coder from the heap.
**
** Unlike heap_pop(), which removes the root,
** this function removes any node whose
** coder_id matches the requested value.
**
** Because heaps are not sorted, we must search
** through the entire array to find the node.
*/
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
