/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   main.c                                             :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: kpanfero <kpanfero@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/10 19:47:13 by Kirill            #+#    #+#             */
/*   Updated: 2025/11/11 13:05:30 by kpanfero         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

char	*get_next_line(int fd);

void	test_only_newlines(void)
{
	int		fd;
	char	*line;
	int		passed;

	fd = open("only_newlines.txt", O_RDONLY);
	passed = 1;
	while ((line = get_next_line(fd)) != NULL)
	{
		if (line[0] != '\n')
		{
			printf("Test Failed: Expected empty string for newline, got '%s'\n",
				line);
			passed = 0;
		}
		free(line);
	}
	if (passed)
	{
		printf("Test Passed: File with only newlines handled correctly\n");
	}
	close(fd);
}

void	test_empty_file(void)
{
	int		fd;
	char	*line;

	fd = open("empty_file.txt", O_RDONLY);
	line = get_next_line(fd);
	if (line == NULL)
	{
		printf("Test Passed: Empty file returns NULL\n");
	}
	else
	{
		printf("Test Failed: Expected NULL, got '%s'\n", line);
		free(line);
	}
	close(fd);
}

void	test_empty_line(void)
{
	int		fd;
	char	*line;

	fd = open("empty_line.txt", O_RDONLY);
	line = get_next_line(fd);
	if (line && line[0] == '\n')
	{
		printf("Test Passed: Single empty line returns empty string\n");
	}
	else
	{
		printf("Test Failed: Expected empty line, got '%s'\n", line);
	}
	free(line);
	close(fd);
}

void	test_multiple_lines(void)
{
	int		fd;
	char	*line;

	fd = open("file_multiple_lines.txt", O_RDONLY);
	line = get_next_line(fd);
	if (line && strcmp(line, "linea 1\n") == 0)
	{
		printf("Test Passed: First line correct\n");
	}
	else
	{
		printf("Test Failed: First line incorrect\n");
	}
	free(line);
	line = get_next_line(fd);
	if (line && strcmp(line, "linea 2\n") == 0)
	{
		printf("Test Passed: Second line correct\n");
	}
	else
	{
		printf("Test Failed: Second line incorrect\n");
	}
	free(line);
	line = get_next_line(fd);
	if (line && line[0] == '\n')
	{
		printf("Test Passed: Empty line correct\n");
	}
	else
	{
		printf("Test Failed: Expected empty line, got '%s'\n", line);
	}
	free(line);
	line = get_next_line(fd);
	if (line && strcmp(line, "linea 3\n") == 0)
	{
		printf("Test Passed: Last line correct\n");
	}
	else
	{
		printf("Test Failed: Last line incorrect\n");
	}
	free(line);
	line = get_next_line(fd);
	if (line == NULL)
	{
		printf("Test Passed: End of file reached\n");
	}
	else
	{
		printf("Test Failed: Expected NULL, got '%s'\n", line);
		free(line);
	}
	close(fd);
}

int	main(void)
{
	/*printf("Starting test...\n\n");
	test_only_newlines();
	test_empty_file();
	test_empty_line();
	test_multiple_lines();
	printf("\nAll tests completed.\n");*/
	int		fd;
	char	*line;

	fd = open("test.txt", O_RDONLY);
	line = get_next_line(fd);
	return (0);
}
