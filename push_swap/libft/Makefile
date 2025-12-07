# **************************************************************************** #
#                                                                              #
#                                                         :::      ::::::::    #
#    Makefile                                           :+:      :+:    :+:    #
#                                                     +:+ +:+         +:+      #
#    By: kpanfero <kpanfero@student.42.fr>          +#+  +:+       +#+         #
#                                                 +#+#+#+#+#+   +#+            #
#    Created: 2025/09/29 17:52:53 by kpanfero          #+#    #+#              #
#    Updated: 2025/10/15 18:20:06 by kpanfero         ###   ########.fr        #
#                                                                              #
# **************************************************************************** #

NAME = libft.a

CC      = cc
CFLAGS += -Wall -Werror -Wextra
RM = rm -f

MY_SOURCES = ft_isdigit.c         \
			 ft_isalpha.c         \
			 ft_isalnum.c         \
			 ft_isascii.c		  \
			 ft_isprint.c		  \
			 ft_strlen.c          \
			 ft_memset.c          \
			 ft_bzero.c			  \
			 ft_memcpy.c		  \
			 ft_memmove.c 		  \
			 ft_strlcpy.c		  \
			 ft_strlcat.c 		  \
			 ft_toupper.c 		  \
			 ft_tolower.c 		  \
			 ft_strchr.c 		  \
			 ft_strrchr.c 		  \
			 ft_strncmp.c 		  \
			 ft_memchr.c 		  \
			 ft_memcmp.c		  \
			 ft_strnstr.c 		  \
			 ft_atoi.c			  \
			 ft_calloc.c 		  \
			 ft_strdup.c          \
			 ft_substr.c 	 	  \
			 ft_strjoin.c		  \
			 ft_strtrim.c	 	  \
			 ft_split.c			  \
			 ft_itoa.c 		      \
			 ft_strmapi.c  		  \
			 ft_striteri.c 		  \
			 ft_putchar_fd.c   	  \
			 ft_putstr_fd.c   	  \
			 ft_putendl_fd.c      \
			 ft_putnbr_fd.c       

BONUS_SRC =  ft_lstnew_bonus.c          \
			 ft_lstadd_front_bonus.c    \
			 ft_lstsize_bonus.c 		\
			 ft_lstlast_bonus.c 		\
			 ft_lstadd_back_bonus.c 	\
			 ft_lstdelone_bonus.c		\
			 ft_lstclear_bonus.c 		\
			 ft_lstiter_bonus.c 		\
			 ft_lstmap_bonus.c          
  
MY_OBJECTS = $(MY_SOURCES:.c=.o)
BONUS_OBJ  = $(BONUS_SRC:.c=.o)

all: $(NAME)

$(NAME): $(MY_OBJECTS)
	ar rcs $(NAME) $(MY_OBJECTS)
	
%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@
	
bonus: $(MY_OBJECTS) $(BONUS_OBJ)
	ar rcs $(NAME) $(MY_OBJECTS) $(BONUS_OBJ)
	
clean:
	$(RM) $(MY_OBJECTS) $(BONUS_OBJ)
	
fclean: clean
	$(RM) $(NAME)
	
re: fclean all
