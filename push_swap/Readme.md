./push_swap $(cat numbers.txt) | wc -l
ARG="1 2 3 6 5"; ./push_swap $ARG | wc -l
valgrind --leak-check=full ./push_swap ""