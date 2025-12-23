/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   push_swap.h                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: kpanfero <kpanfero@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/07 12:34:46 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/08 09:23:51 by kpanfero         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef PUSH_SWAP_H
# define PUSH_SWAP_H

# include <unistd.h>
# include <stdlib.h>
# include <stdio.h>
# include "../libft/libft.h"
# include <limits.h>

typedef struct s_stack
{
	int				value;
	int				index;
	struct s_stack	*next;
}	t_stack;

void	pa(t_stack **a, t_stack **b);
void	pb(t_stack **a, t_stack **b);
void	rra(t_stack **a);
void	rrb(t_stack **b);
void	rrr(t_stack **a, t_stack **b);
void	ra(t_stack **a);
void	rb(t_stack **b);
void	rr(t_stack **a, t_stack **b);
void	sa(t_stack **a);
void	sb(t_stack **b);
void	ss(t_stack **a, t_stack **b);
void	free_split(char **res);
void	lst_addback(t_stack **lst, t_stack *new_node);
void	clear_stack(t_stack **lst);
void	assign_indices(t_stack *a);
void	sort_two(t_stack **a);
void	sort_three(t_stack **a);
void	sort_four(t_stack **a, t_stack **b);
void	sort_five(t_stack **a, t_stack **b);
void	sort_big_list(t_stack **a, t_stack **b, int size);
char	*join_args(int argc, char **argv);
char	**split_args(int argc, char **argv);
char	**validate_args(int argc, char **argv);
int		check_duplicates(char **values);
int		is_valid_int(char *str);
int		atoi_safe(char *str);
int		is_sorted(t_stack *a);
int		list_size(t_stack *begin_list);
int		find_min(t_stack *a);
int		get_dir(t_stack *a);
t_stack	*lst_new(int value);
t_stack	*create_stack(int argc, char **argv);

#endif