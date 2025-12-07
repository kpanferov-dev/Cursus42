/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   sort_utils.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/07 12:38:21 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/07 12:38:21 by Kirill           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "push_swap.h"

int	is_sorted(t_stack *a)
{
	if (!a || !a->next)
		return (1);
	while (a->next != NULL && a->value < a->next->value)
		a = a->next;
	if (a->next == NULL)
		return (1);
	return (0);
}

int list_size(t_stack *stack)
{
    int i = 0;

    while (stack)
    {
        i++;
        stack = stack->next;
    }
    return i;
}

int	find_min(t_stack *a)
{
	int	min;

	min = INT_MAX;
	while (a)
	{
		if (a->value < min)
			min = a->value;
		a = a->next;
	}
	return (min);
}

int	get_dir(t_stack *a)
{
	int	smallest;
	int	index;
	int	smallest_index;
	int	half;

	index = 0;
	smallest_index = 0;
	smallest = INT_MAX;
	half = list_size(a) / 2;
	while (a)
	{
		if (a->value < smallest)
		{
			smallest = a->value;
			smallest_index = index;
		}
		a = a->next;
		index++;
	}
	if (smallest_index < half)
		return (1);
	else
		return (-1);
}
