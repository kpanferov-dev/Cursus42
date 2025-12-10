/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_strcspn.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/10 16:48:53 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/10 16:48:53 by Kirill           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdio.h>

size_t	ft_strcspn(const char *s, const char *reject)
{
    int     i = 0;
    int     j = 0;

    while(s[i] != '\0')
    {
        j = 0;
        while(reject[j] != '\0')
        {
            if(s[i] == reject[j])
                return i;
            j++;
        }
        i++;
    }
}