/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   swap.c                                             :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/07 12:30:28 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/07 12:30:28 by Kirill           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "../push_swap.h"

void	sa(t_stack **a)
{
	t_stack	*first;
	t_stack	*second;
	int		temp;

	if (!a || !*a || !(*a)->next)
		return ;
	first = *a;
	second = (*a)->next;
	temp = first->value;
	first->value = second->value;
	second->value = temp;
	write (1, "sa\n", 3);
}

void	sb(t_stack **b)
{
	t_stack	*first;
	t_stack	*second;
	int		temp;

	if (!b || !*b || !(*b)->next)
		return ;
	first = *b;
	second = (*b)->next;
	temp = first->value;
	first->value = second->value;
	second->value = temp;
	write (1, "sb\n", 3);
}

void	ss(t_stack **a, t_stack **b)
{
	t_stack	*first;
	t_stack	*second;
	int		temp;

	if (!a || !*a || !(*a)->next)
		return ;
	first = *a;
	second = (*a)->next;
	temp = first->value;
	first->value = second->value;
	second->value = temp;
	if (!b || !*b || !(*b)->next)
		return ;
	first = *b;
	second = (*b)->next;
	temp = first->value;
	first->value = second->value;
	second->value = temp;
	write (1, "ss\n", 3);
}