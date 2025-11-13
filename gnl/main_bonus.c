/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   main_bonus.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: kpanfero <kpanfero@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/10 15:59:54 by Kirill            #+#    #+#             */
/*   Updated: 2025/11/13 10:03:13 by kpanfero         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */


#include <stdio.h>
#include <fcntl.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include "get_next_line_bonus.h"

void test_only_newlines() {
    int fd = open("only_newlines.txt", O_RDONLY);
    char *line;
    int passed = 1;

    while ((line = get_next_line(fd)) != NULL) {
        if (line[0] != '\n') {
            printf("Test Failed: Expected empty string for newline, got '%s'\n", line);
            passed = 0;
        }
        free(line);
    }

    if (passed) {
        printf("Test Passed: File with only newlines handled correctly\n");
    }

    close(fd);
}

void test_empty_file() {
    int fd = open("empty_file.txt", O_RDONLY);
    char *line = get_next_line(fd);

    if (line == NULL) {
        printf("Test Passed: Empty file returns NULL\n");
    } else {
        printf("Test Failed: Expected NULL, got '%s'\n", line);
        free(line);
    }

    close(fd);
}

void test_empty_line() {
    int fd = open("empty_line.txt", O_RDONLY);
    char *line = get_next_line(fd);

    if (line && line[0] == '\n') {
        printf("Test Passed: Single empty line returns empty string\n");
    } else {
        printf("Test Failed: Expected empty line, got '%s'\n", line);
    }

    free(line);
    close(fd);
}

void test_custom_file(char  *file) {
    int fd = open(file, O_RDONLY);
    char *line;

    if (fd < 0)
    {
        printf("File doesnt exist\n");
    }
        
    while ((line = get_next_line(fd)))
    {
        printf("%s\n",line);
        free(line);  
    }
    close(fd);
}

void test_multiple_lines() {
    int fd = open("file_multiple_lines.txt", O_RDONLY);
    char *line;

    line = get_next_line(fd);
    if (line && strcmp(line, "linea 1\n") == 0) {
        printf("Test Passed: First line correct\n");
    } else {
        printf("Test Failed: First line incorrect\n");
    }
    free(line);

    line = get_next_line(fd);
    if (line && strcmp(line, "linea 2\n") == 0) {
        printf("Test Passed: Second line correct\n");
    } else {
        printf("Test Failed: Second line incorrect\n");
    }
    free(line);

    line = get_next_line(fd);
    if (line && line[0] == '\n') {
        printf("Test Passed: Empty line correct\n");
    } else {
        printf("Test Failed: Expected empty line, got '%s'\n", line);
    }
    free(line);

    line = get_next_line(fd);
    if (line && strcmp(line, "linea 3\n") == 0) {
        printf("Test Passed: Last line correct\n");
    } else {
        printf("Test Failed: Last line incorrect\n");
    }
    free(line);

    line = get_next_line(fd);
    if (line == NULL) {
        printf("Test Passed: End of file reached\n");
    } else {
        printf("Test Failed: Expected NULL, got '%s'\n", line);
        free(line);
    }

    close(fd);
}

void test_files_bonus(char **files, int count)
{
    int *fds = malloc(sizeof(int) * count);
    char **lines = malloc(sizeof(char *) * count);
    int finished = 0;

    for (int i = 0; i < count; i++)
    {
        fds[i] = open(files[i], O_RDONLY);
        if (fds[i] < 0)
        {
            printf("Error opening file: %s\n", files[i]);
            lines[i] = NULL;
        }
        else
            lines[i] = NULL;
    }

    while (!finished)
    {
        finished = 1;
        for (int i = 0; i < count; i++)
        {
            if (!lines[i])
            {
                lines[i] = get_next_line(fds[i]);
                if (lines[i])
                {
                    printf("[%s] %s", files[i], lines[i]);
                    free(lines[i]);
                    lines[i] = NULL;
                    finished = 0;
                }
            }
        }
    }

    for (int i = 0; i < count; i++)
        if (fds[i] >= 0) close(fds[i]);

    free(fds);
    free(lines);
}

void test_stdin_bonus(void) {
    
    char *line;
    printf("Type something , Ctrl + C to exit or \"all\" for all tests \n\n");
    while ((line = get_next_line(0)) != NULL)
    {
        if (strcmp(line,"all\n") == 0)
        {
            printf("\n");
            test_empty_file();
            test_only_newlines();
            test_empty_line();
            test_multiple_lines();
            printf("\n");
        }
        else
            printf("Stdin: %s\n", line);
        free(line);
    }
}

int main(int argc, char **argv)
{
    printf("Starting test (BONUS)...\n\n");

    if (argc > 1)
        test_files_bonus(argv + 1, argc - 1);
    else
        test_stdin_bonus();

    printf("\nAll tests completed.\n");
    return 0;
}
