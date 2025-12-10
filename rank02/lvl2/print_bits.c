/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   print_bits.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/10 18:17:07 by Kirill            #+#    #+#             */
/*   Updated: 2025/12/10 18:17:07 by Kirill           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

void	print_bits(unsigned char octet)
{
    int i = 8;
    unsigned char bit;

    while(i--)
    {
        bit = (octet >> i & 1) + '0';
        write(write(1, &bit, 1));
    }
}