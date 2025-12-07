/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_split.c                                         :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: kpanfero <kpanfero@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/08 17:48:39 by kpanfero          #+#    #+#             */
/*   Updated: 2025/10/15 18:41:38 by kpanfero         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdlib.h>

static int	count_words(const char *s, char c)
{
	int	count;
	int	in_word;

	count = 0;
	in_word = 0;
	while (*s)
	{
		if (*s != c && in_word == 0)
		{
			in_word = 1;
			count++;
		}
		else if (*s == c)
			in_word = 0;
		s++;
	}
	return (count);
}

static char	*word_dup(const char *start, int len)
{
	char	*word;
	int		i;

	word = (char *)malloc(len + 1);
	i = 0;
	if (!word)
		return (NULL);
	while (i < len)
	{
		word[i] = start[i];
		i++;
	}
	word[len] = '\0';
	return (word);
}

static void	free_all(char **arr, int i)
{
	while (i-- > 0)
		free(arr[i]);
	free(arr);
}

static char	**ft_split_aux(char const *s, char c, int words, char **result)
{
	int			i;
	int			len;
	const char	*start;

	i = 0;
	if (!result)
		return (NULL);
	while (*s && i < words)
	{
		while (*s == c)
			s++;
		start = s;
		len = 0;
		while (*s && *s++ != c)
			len++;
		result[i] = word_dup(start, len);
		if (!result[i])
		{
			free_all(result, i);
			return (NULL);
		}
		i++;
	}
	result[i] = NULL;
	return (result);
}

char	**ft_split(char const *s, char c)
{
	int			words;
	char		**result;

	if (!s)
		return (NULL);
	words = count_words(s, c);
	result = (char **)malloc((words + 1) * sizeof(char *));
	if (!result)
		return (NULL);
	return (ft_split_aux(s, c, words, result));
}
