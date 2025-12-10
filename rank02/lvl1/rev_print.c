/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   rev_print.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/10 13:51:28 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/10 13:51:28 by Kirill           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <unistd.h>

void    write_rev(char *str)
{
    int i = 0;
    while(str[i] !=  '\0')
        i++;
    i--;  
    while (i >= 0)
    {
        write(1, &str[i], 1);
        i--;
    }
}
int main(int argc, char ** argv)
{
    if(argc == 2)
        write_rev(argv[1]);

    write(1,"\n",1);
    return 0;
}