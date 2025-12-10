# **************************************************************************** #
#                                                                              #
#                                                         :::      ::::::::    #
#    ft_water_reminder.py                               :+:      :+:    :+:    #
#                                                     +:+ +:+         +:+      #
#    By: Kirill <kpanfero@student.42madrid.com>     +#+  +:+       +#+         #
#                                                 +#+#+#+#+#+   +#+            #
#    Created: 2025/12/10 11:27:31 by Kirill            #+#    #+#              #
#    Updated: 2025/12/10 11:27:31 by Kirill           ###   ########.fr        #
#                                                                              #
# **************************************************************************** #

def  ft_water_reminder():
    days = int(input("Days since last watering: "))
    if days > 2:
        print("Water the plants!",end = "")
    else:
        print("Plants are fine",end = "")    