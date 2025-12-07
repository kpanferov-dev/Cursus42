/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   sort_big.c                                         :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/07 12:36:56 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/07 12:36:56 by Kirill           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "push_swap.h"

void	sort_big_list(t_stack **a, t_stack **b, int size)
{
	int	i;
	int	j;
	int	num;
	int	max_bits;

	i = 0;
	max_bits = 0;
	while ((size - 1) >> max_bits)
		max_bits++;
	while (i < max_bits)
	{
		j = 0;
		while (j < size)
		{
			num = (*a)->index;
			if (((num >> i) & 1) == 0)
				pb(a, b);
			else
				ra(a);
			j++;
		}
		while (*b)
			pa(a, b);
		i++;
	}
}

void	assign_indices(t_stack *a)
{
	t_stack	*current;
	t_stack	*compare;
	int		index;

	current = a;
	while (current)
	{
		index = 0;
		compare = a;
		while (compare)
		{
			if (compare->value < current->value)
				index++;
			compare = compare->next;
		}
		current->index = index;
		current = current->next;
	}
}