/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_rrange.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/10 21:06:38 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/10 21:06:38 by Kirill           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdlib.h>

int *ft_rrange(int start, int end)
{
    int len;
    int *res;
    int i = 0;

    if (start < end)
        len = end - start + 1;
    else
        len = start - end + 1;

    res = malloc(sizeof(int) * len);
    if (!res)
        return NULL;

    if (start < end)
    {

        while (i < len)
        {
            res[i] = end;
            end--;
            i++;
        }
    }
    else
    {
        while (i < len)
        {
            res[i] = end;
            end++;
            i++;
        }
    }

    return res;
}
