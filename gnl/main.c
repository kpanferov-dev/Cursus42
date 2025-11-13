/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   main.c                                             :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: kpanfero <kpanfero@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/10 19:47:13 by Kirill            #+#    #+#             */
/*   Updated: 2025/11/13 10:02:20 by kpanfero         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdio.h>
#include <fcntl.h>
#include <string.h>
#include <unistd.h>
#include "get_next_line.h"

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

void test_stdin(void) {
    
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

int main(int argc,char **argv) {
 
    printf("Starting test...\n\n");
    if (argc == 2)
    {
        if (strcmp(argv[1],"empty_file.txt") == 0)
            test_empty_file();
        else if (strcmp(argv[1],"only_newlines.txt") == 0)
            test_only_newlines();
        else if (strcmp(argv[1],"empty_line.txt") == 0)
            test_empty_line();
        else if (strcmp(argv[1],"multiple_lines.txt") == 0)
            test_multiple_lines();
        else
            test_custom_file(argv[1]);       
    }
    else if (argc == 1)
        test_stdin(); 
    else
        printf("Error\n");
        
    printf("\nAll tests completed.\n");

    return 0;
}
