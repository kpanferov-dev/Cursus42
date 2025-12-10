/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   rotone.c                                           :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/10 14:12:30 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/10 14:12:30 by Kirill           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <unistd.h>

void rot(char *str)
{
    while(*str){

        if (*str >= 'a' && *str <= 'z')
            *str = (*str - 'a' + 1) % 26 + 'a';
        else if (*str >= 'A' && *str <= 'Z')
            *str = (*str - 'A' + 1) % 26 + 'A';
        write(1,str,1);
        str++;
    }
}

int main(int ac, char **av)
{
    if (ac == 2)
        rot(av[1]);

    write(1,"\n",1);
    return 0;
}