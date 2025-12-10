/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   repeat_alhpa.c                                     :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/10 13:41:24 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/10 13:41:24 by Kirill           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <unistd.h>
void    repeat_alpha(char *str)
{
    int i = 0, repeat = 0;
   
    while (str[i])
    {
        if (*str >= 'a' && *str <= 'z')
            repeat = str[i] - 'a' + 1;
        else if (*str >= 'A' && *str <= 'Z')
            repeat = str[i] - 'A' + 1;
        else
            repeat = 1;
        for (int j = 0; j < repeat; j++)
            write(1, &str[i], 1);
        i++;
    }
}

int main(int argc, char **argv)
{
    if (argc == 2)
        repeat_alpha(argv[1]);
    
    write(1, "\n", 1);
    return (0);
}