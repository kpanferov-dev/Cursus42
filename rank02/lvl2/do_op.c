/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   do_op.c                                            :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/10 15:57:16 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/10 15:57:16 by Kirill           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
int main(int ac, char **av)
{
    int a = atoi(av[1]);
    int b = atoi(av[3]);
    if(ac == 4)
    {
        if(av[2][0] == '+')
            printf("%d", (a + b));
        if(av[2][0] == '-')
            printf("%d", (a - b));
        if(av[2][0] == '/')
            printf("%d", (a / b));
        if(av[2][0] == '*')
            printf("%d", (a * b));
        if(av[2][0] == '%')
            printf("%d", (a % b));

    }
    write(1,"\n",1);
    return 0;
}