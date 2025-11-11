/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   get_next_line.c                                    :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: kpanfero <kpanfero@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/28 11:30:19 by kpanfero          #+#    #+#             */
/*   Updated: 2025/11/11 16:45:41 by kpanfero         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "get_next_line.h"
#include <unistd.h>

char	*read_fd(int fd, char *stash)
{
	char	*aux;
	size_t	bytes_read;

	aux = (char *)malloc(BUFFER_SIZE + 1);
	if (!aux)
		return (NULL);
	bytes_read = 1;
	while (bytes_read > 0 && !ft_strchr(stash, '\n'))
	{
		bytes_read = read(fd, aux, BUFFER_SIZE);
		if (bytes_read == -1)
		{
			free(aux);
			return (NULL);
		}
		aux[bytes_read] = '\0';
		stash = ft_strjoin(stash, aux);
	}
	free(aux);
	return (stash);
}

char	*get_line(char *stash)
{
	char	*line;
	size_t	i;

	i = 0;
	while (stash[i] != '\n')
		i++;

	line = NULL;
	return (line);
}

char	*get_next_line(int fd)
{
	static char	*stash;
	char		*line;

	if (fd < 0 || BUFFER_SIZE <= 0)
		return (NULL);
	stash = read_fd(fd, stash);
	if (!stash)
		return (NULL);
	line = get_line(stash);
	/*
	stash = get_rest(stash);
	return (line);*/
	return (NULL);
}
