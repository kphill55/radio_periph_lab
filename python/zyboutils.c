# include <stdio.h>
# include <string.h> // memcpy
# include <stdlib.h> // strtol
# include <fcntl.h>
# include <sys/mman.h>
# include <unistd.h>
# include <sys/time.h>

# define PAGE_SIZE 4096

typedef struct virtual_mem_map {
    void* virt_addr;
    int fd;
} virtual_mem_map_t;

virtual_mem_map_t* map_mem(unsigned phys_addr) {
    void * virt_addr;

    unsigned base_addr = phys_addr & -PAGE_SIZE;

    int fd = open("/dev/mem", O_RDWR | O_SYNC);
    printf("Opened file descriptor: %d\n", fd);
    virt_addr = mmap(NULL, PAGE_SIZE, PROT_READ |
                     PROT_WRITE, MAP_SHARED, fd, base_addr);
    if (virt_addr == MAP_FAILED) {
        return NULL;
    }
    printf("Mapped physical address %p to virtual address: %p\n", phys_addr, virt_addr);
    
    virtual_mem_map_t s_temp = {virt_addr, fd};
    virtual_mem_map_t* s = malloc(sizeof(virtual_mem_map_t));
    *s = s_temp;
    printf("Storing fd and virt addr in struct at: %p\n", s);

    return s;
}

void unmap_mem(virtual_mem_map_t* s) {
    printf("Unmapping virt address: %p\n", s->virt_addr);
    munmap(s->virt_addr, PAGE_SIZE);
    printf("Closing file descriptor: %d\n", s->fd);
    close(s->fd);
    printf("Freeing struct at: %p\n", s);
    free(s);
}

int write_reg(virtual_mem_map_t* s, unsigned addr, unsigned val){
    unsigned page_offset = addr % PAGE_SIZE;

    * (volatile unsigned*)(s->virt_addr+page_offset) = val;

    return 0;
}

int read_reg(virtual_mem_map_t* s, unsigned addr, unsigned * val){
    unsigned page_offset = addr % PAGE_SIZE;

    * val = *(volatile unsigned*)(s->virt_addr+page_offset);

    return 0;
}

// int write_reg(unsigned addr, unsigned val){
//     void * virt_addr;

//     unsigned page_offset = addr % PAGE_SIZE;
//     unsigned base_addr = addr & -PAGE_SIZE;

//     int fd = open("/dev/mem", O_RDWR | O_SYNC);
//     virt_addr = mmap(NULL, PAGE_SIZE, PROT_READ |
//                      PROT_WRITE, MAP_SHARED, fd, base_addr);

//     if (virt_addr == MAP_FAILED) {
//         return -1;
//     }

//     * (volatile unsigned*)(virt_addr+page_offset) = val;

//     munmap(virt_addr, PAGE_SIZE);
//     close(fd);
//     return 0;
// }

// int read_reg(unsigned addr, unsigned * val){
//     void * virt_addr;

//     unsigned page_offset = addr % PAGE_SIZE;
//     unsigned base_addr = addr & -PAGE_SIZE;

//     int fd = open("/dev/mem", O_RDWR | O_SYNC);
//     virt_addr = mmap(NULL, PAGE_SIZE, PROT_READ |
//                      PROT_WRITE, MAP_SHARED, fd, base_addr);

//     if (virt_addr == MAP_FAILED) {
//         return -1;
//     }

//     * val = *(volatile unsigned*)(virt_addr+page_offset);

//     munmap(virt_addr, PAGE_SIZE);
//     close(fd);
//     return 0;
// }
