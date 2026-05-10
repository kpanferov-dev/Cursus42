NAME        = codexion
CC          = gcc
CFLAGS      = -Wall -Wextra -Werror -pthread
INC         = -I inc
SRC_DIR     = src
SRC         = $(SRC_DIR)/main.c $(SRC_DIR)/parse.c $(SRC_DIR)/sim.c \
              $(SRC_DIR)/coder.c $(SRC_DIR)/dongle.c $(SRC_DIR)/monitor.c \
              $(SRC_DIR)/priority_queue.c $(SRC_DIR)/utils.c
OBJ         = $(SRC:.c=.o)

all: $(NAME)

$(NAME): $(OBJ)
	$(CC) $(CFLAGS) $(INC) $(OBJ) -o $(NAME)

%.o: %.c
	$(CC) $(CFLAGS) $(INC) -c $< -o $@

clean:
	rm -f $(OBJ)

fclean: clean
	rm -f $(NAME)

re: fclean all

.PHONY: all clean fclean re

#valgrind --leak-check=full --show-leak-kinds=all --track-origins=yes ./codexion 4 800 200 200 200 5 50 fifo