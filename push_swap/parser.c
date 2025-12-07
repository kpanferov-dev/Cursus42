/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   parser.c                                           :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/07 12:33:55 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/07 12:33:55 by Kirill           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "push_swap.h"

void	free_split(char **res)
{
	int	j;

	j = 0;
	if (!res)
		return ;
	while (res[j])
	{
		free(res[j]);
		j++;
	}
	free(res);
}

char	*join_args(int argc, char **argv)
{
	char	*joined;
	char	*ptr;
	int		i;
	int		j;
	int		len;

	len = 0;
	i = -1;
	while (++i < argc)
		len += ft_strlen(argv[i]) + (i < argc - 1);
	joined = malloc(len + 1);
	if (!joined)
		return (NULL);
	ptr = joined;
	i = -1;
	while (++i < argc)
	{
		j = -1;
		while (argv[i][++j])
			*ptr++ = argv[i][j];
		if (i < argc - 1)
			*ptr++ = ' ';
	}
	return (*ptr = '\0', joined);
}

char	**split_args(int argc, char **argv)
{
	char	*joined;
	char	**values;

	joined = join_args(argc, argv);
	if (!joined)
		return (NULL);
	values = ft_split(joined, ' ');
	free(joined);
	return (values);
}

int	is_valid_int(char *str)
{
	int		i;
	int		sign;
	long	n;

	i = 0;
	sign = 1;
	n = 0;
	while ((str[i] >= 9 && str[i] <= 13) || str[i] == ' ')
		i++;
	if (str[i] == '-' || str[i] == '+')
	{
		if (str[i] == '-')
			sign = -1;
		i++;
	}
	while (ft_isdigit(str[i]))
	{
		n = n * 10 + (str[i++] - '0');
		if ((sign == 1 && n > INT_MAX) || (sign == -1 && -(n) < INT_MIN))
			return (0);
	}
	if (str[i] != '\0')
		return (0);
	return (1);
}

int	check_duplicates(char **values)
{
	int	i;
	int	n1;
	int	j;
	int	n2;

	i = 0;
	while (values[i])
	{
		n1 = atoi_safe(values[i]);
		j = i + 1;
		while (values[j])
		{
			n2 = atoi_safe(values[j]);
			if (n1 == n2)
				return (0);
			j++;
		}
		i++;
	}
	return (1);
}
