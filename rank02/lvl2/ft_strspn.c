/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_strspn.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/10 17:35:02 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/10 17:35:02 by Kirill           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */
#include <stdio.h>
size_t	ft_strspn(const char *s, const char *accept)
{
    size_t i = 0;
    size_t j;

    while (s[i])
    {
        j = 0;
        while(accept[j])
        {
            if(s[i] == accept[j])
                break;
            j++;
        }
        if(accept[j] == '\0')
            return i;
        i++;
    }
    return i;
}