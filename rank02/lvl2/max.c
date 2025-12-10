/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   max.c                                              :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/10 18:12:22 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/10 18:12:22 by Kirill           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <limits.h>
int		max(int* tab, unsigned int len)
{
    unsigned int max;
	unsigned int i = 0;
	
	max = tab[i];
	while(i < len)
	{
		if (max <  tab[i])
		{
			max = tab[i];
		}
		i++;
	}
	return max;
}