/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_strlcpy.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: kpanfero <kpanfero@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/02 10:40:51 by kpanfero          #+#    #+#             */
/*   Updated: 2025/10/15 11:38:07 by kpanfero         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stddef.h>

void	*ft_memcpy(void *dest, const void *src, size_t n);
size_t	ft_strlen(const char *s);

size_t	ft_strlcpy(char *dst, const char *src, size_t size)
{
	size_t	len;
	size_t	len2;

	len = ft_strlen(src);
	if (len >= size)
		len2 = size - 1;
	else
		len2 = len;
	if (size != 0)
	{
		ft_memcpy(dst, src, len2);
		dst[len2] = '\0';
	}
	return (len);
}
