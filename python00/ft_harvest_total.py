# **************************************************************************** #
#                                                                              #
#                                                         :::      ::::::::    #
#    ft_harvest_total.py                                :+:      :+:    :+:    #
#                                                     +:+ +:+         +:+      #
#    By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+         #
#                                                 +#+#+#+#+#+   +#+            #
#    Created: 2025/12/10 11:11:34 by Kirill            #+#    #+#              #
#    Updated: 2025/12/10 11:11:34 by Kirill           ###   ########.fr        #
#                                                                              #
# **************************************************************************** #

def ft_harvest_total():
    total = 0
    for i in range(1,4):
        total += int(input(f"Day {i} harvest: "))
    print(f"Total harvest: {total}")