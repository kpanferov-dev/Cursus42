# **************************************************************************** #
#                                                                              #
#                                                         :::      ::::::::    #
#    ft_count_harvest_recursive.py                      :+:      :+:    :+:    #
#                                                     +:+ +:+         +:+      #
#    By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+         #
#                                                 +#+#+#+#+#+   +#+            #
#    Created: 2025/12/10 11:33:52 by Kirill            #+#    #+#              #
#    Updated: 2025/12/10 11:33:52 by Kirill           ###   ########.fr        #
#                                                                              #
# **************************************************************************** #

def ft_count_harvest_recursive():
    days = int(input("Days until harvest: "))
    
    def helper(current):
        if current > days:
            print("Harvest time!")
        else:
            print(f"Day {current}")
            helper(current + 1)
    helper(1)

