/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   sort_small.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: kpanfero <kpanfero@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/07 12:37:41 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/08 09:23:42 by kpanfero         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "push_swap.h"

void	sort_two(t_stack **a)
{
	sa(a);
}

void	sort_three(t_stack **a)
{
	while (!is_sorted(*a))
	{
		if ((*a)->value > (*a)->next->value)
		{
			sa(a);
		}
		else
			rra(a);
	}
}

void	sort_four(t_stack **a, t_stack **b)
{
	int	dir;

	dir = get_dir(*a);
	while ((*a)->value != find_min(*a))
	{
		if (dir == 1)
			ra(a);
		else
			rra(a);
	}
	pb(a, b);
	sort_three(a);
	pa(a, b);
}

void	sort_five(t_stack **a, t_stack **b)
{
	int	dir;

	dir = get_dir(*a);
	while ((*a)->value != find_min(*a))
	{
		if (dir == 1)
			ra(a);
		else
			rra(a);
	}
	pb(a, b);
	sort_four(a, b);
	pa(a, b);
}
