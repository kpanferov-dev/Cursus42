/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   push_swap.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/07 12:34:25 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/07 12:34:25 by Kirill           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "push_swap.h"

char	**validate_args(int argc, char **argv)
{
	char	**values;
	int		i;

	values = split_args(argc - 1, argv + 1);
	i = 0;
	if (!values)
		return (write(1, "Error\n", 6), NULL);
	i = 0;
	while (values[i])
	{
		if (!is_int_atoi(values[i]))
			return (free_split(values), write(2, "Error\n", 6), NULL);
		i++;
	}
	if (!check_duplicates(values))
		return (free_split(values), write(2, "Error\n", 6), NULL);
	return (values);
}

void	print_stack(t_stack *stack)
{
	int	i;

	i = 0;
	while (stack)
	{
		printf("Node[%d]: %d\n", i, stack->value);
		// printf("index[%d]: %d\n", i, stack->index);
		stack = stack->next;
		i++;
	}
}

static void	sort(t_stack **a, t_stack **b)
{
	int	len;

	len = list_size(*a);
	if (is_sorted(*a) == 1)
		return ;
	else if (len == 1)
		return ;
	else if (len == 2)
		sort_two(a);
	else if (len == 3)
		sort_three(a);
	else if (len == 4)
		sort_four(a, b);
	else if (len == 5)
		sort_five(a, b);
	else if (len > 5)
		sort_big_list(a, b, len);
	else
		return ;
}

int	main(int argc, char **argv)
{
	t_stack	*a;
	t_stack	*b;

	a = NULL;
	b = NULL;
	if (argc < 2)
		return (0);
	a = create_stack(argc, argv);
	print_stack(a);
	if (!a)
		return (1);
	assign_indices(a);
	sort(&a, &b);
	print_stack(a);
	clear_stack(&a);
	clear_stack(&b);
	return (0);
}