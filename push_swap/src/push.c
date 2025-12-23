/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   push.c                                             :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: kpanfero <kpanfero@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/07 12:29:09 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/08 09:24:35 by kpanfero         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "../push_swap.h"

static void	push(t_stack **dst, t_stack **src)
{
	t_stack	*first;

	if (!src || !*src)
		return ;
	first = *src;
	*src = (*src)->next;
	first->next = *dst;
	*dst = first;
}

void	pa(t_stack **a, t_stack **b)
{
	push(a, b);
	write(1, "pa\n", 3);
}

void	pb(t_stack **a, t_stack **b)
{
	push(b, a);
	write(1, "pb\n", 3);
}
