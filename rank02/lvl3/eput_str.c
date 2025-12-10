/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   eput_str.c                                         :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/10 20:12:19 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/10 20:12:19 by Kirill           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

int main(int argc, char const *argv[])
{
    int i;
    int flag = 0;

    if (argc == 2)
    {
        i = 0;
        while (argv[1][i] == ' ' || argv[1][i] == '\t')
            i++;

        while (argv[1][i])
        {
            if (argv[1][i] == ' ' || argv[1][i] == '\t')
                flag = 1;
            else
            {
                if (flag)
                    write(1, " ", 1);
                flag = 0;
                write(1, &argv[1][i], 1);
            }
            i++;
        }
    }
    write(1, "\n", 1);
    return 0;
}
