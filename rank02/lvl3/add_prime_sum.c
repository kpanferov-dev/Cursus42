/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   add_prime_sum.c                                    :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/10 19:04:03 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/10 19:04:03 by Kirill           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <unistd.h>
#include <stdlib.h>

int is_prime(int n)
{
    int i;

    if (n < 2)
        return 0;
    for (i = 2; i * i <= n; i++)
    {
        if (n % i == 0)
            return 0;
    }
    return 1;
}

void ft_putnbr(int n)
{
    char c;
    if (n >= 10)
        ft_putnbr(n / 10);
    c = n % 10 + '0';
    write(1, &c, 1);
}

int main(int argc, char **argv)
{
    int i;
    int num;
    int sum = 0;

    if (argc != 2)
    {
        write(1, "0\n", 2);
        return 0;
    }

    num = atoi(argv[1]);
    if (num <= 0)
    {
        write(1, "0\n", 2);
        return 0;
    }

    for (i = 2; i <= num; i++)
    {
        if (is_prime(i))
            sum += i;
    }

    ft_putnbr(sum);
    write(1, "\n", 1);
    return 0;
}
