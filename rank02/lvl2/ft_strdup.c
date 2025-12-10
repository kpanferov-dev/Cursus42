/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_strdup.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/10 17:02:13 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/10 17:02:13 by Kirill           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdlib.h>

char	*ft_strdup(char *src)
{
    int i = 0;
    int length = 0;
    char *dst;

    while(src[length])
        length++;
    dst = malloc(length + 1);
    if(!dst)
        return NULL;
    for(int i = 0; i <= length; i++)
        dst[i] = src[i];
    return (dst);
}