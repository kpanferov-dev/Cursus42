/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   max.c                                              :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: kpanfero <kpanfero@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/10 18:12:22 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/11 15:28:26 by kpanfero         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */


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