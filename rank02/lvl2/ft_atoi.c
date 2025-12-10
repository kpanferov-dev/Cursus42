/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_atoi.c                                          :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/10 16:32:52 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/10 16:32:52 by Kirill           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

int	ft_atoi(const char *str)
{
    int result = 0;
    int sign = 0;

    while(*str == ' ' || (*str >= 9 && *str <= 13))
        str++;
    if(*str == '-')
        sign = -1;
    if(*str == '-' || *str == '+')
        str++;
    while (*str >= '0' && *str <= '9')
    {
        result = result * 10 + *str - '0';
		str++;
    }
    return (sign * result);
}