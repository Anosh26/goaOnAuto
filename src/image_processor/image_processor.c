#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

typedef struct {
    int x, y;
} Point;

typedef struct {
    unsigned char *data;
    int size;
    int capacity;       // Track actual allocated space
    int has_error;      // Track silent failures
} MemoryBuffer;

void write_to_memory(void *context, void *data, int size) {
    MemoryBuffer *buf = (MemoryBuffer *)context;
    
    // Fast fail if a previous write failed
    if (buf->has_error) return; 

    // Geometric growth allocation
    if (buf->size + size > buf->capacity) {
        // Double capacity, or set to initial size if 0
        int new_capacity = buf->capacity == 0 ? 1024 : buf->capacity;
        while (new_capacity < buf->size + size) {
            new_capacity *= 2; 
        }

        unsigned char *new_ptr = realloc(buf->data, new_capacity);
        if (!new_ptr) {
            fprintf(stderr, "Fatal: Buffer reallocation failed\n");
            buf->has_error = 1;
            return;
        }
        
        buf->data = new_ptr;
        buf->capacity = new_capacity;
    }

    // Append data
    memcpy(buf->data + buf->size, data, size);
    buf->size += size;
}

// Bilinear interpolation resize function (RGB 3-channels)
void resize_bilinear(const unsigned char *src, int src_w, int src_h,
                     unsigned char *dest, int dest_w, int dest_h) {
    float x_ratio = ((float)(src_w - 1)) / dest_w;
    float y_ratio = ((float)(src_h - 1)) / dest_h;
    
    for (int i = 0; i < dest_h; i++) {
        for (int j = 0; j < dest_w; j++) {
            int x = (int)(x_ratio * j);
            int y = (int)(y_ratio * i);
            float x_diff = (x_ratio * j) - x;
            float y_diff = (y_ratio * i) - y;
            
            int n1_idx = (y * src_w + x) * 3;
            int n2_idx = n1_idx + 3;
            int n3_idx = n1_idx + src_w * 3;
            int n4_idx = n3_idx + 3;
            
            // Boundary safety
            if (x >= src_w - 1) {
                n2_idx = n1_idx;
                n4_idx = n3_idx;
            }
            if (y >= src_h - 1) {
                n3_idx = n1_idx;
                n4_idx = n2_idx;
            }
            
            for (int c = 0; c < 3; c++) {
                float a = src[n1_idx + c];
                float b = src[n2_idx + c];
                float d = src[n3_idx + c];
                float e = src[n4_idx + c];
                
                float val = a * (1 - x_diff) * (1 - y_diff) +
                            b * (x_diff) * (1 - y_diff) +
                            d * (y_diff) * (1 - x_diff) +
                            e * (x_diff) * (y_diff);
                
                dest[(i * dest_w + j) * 3 + c] = (unsigned char)val;
            }
        }
    }
}

// Samples top corners to estimate average background RGB
void get_average_bg(const unsigned char *data, int width, int height,
                    int *bg_r, int *bg_g, int *bg_b) {
    long r_sum = 0, g_sum = 0, b_sum = 0;
    int count = 0;
    int sample_size = 5;
    
    // Top-left corner
    for (int y = 0; y < sample_size && y < height; y++) {
        for (int x = 0; x < sample_size && x < width; x++) {
            int idx = (y * width + x) * 3;
            r_sum += data[idx];
            g_sum += data[idx + 1];
            b_sum += data[idx + 2];
            count++;
        }
    }
    
    // Top-right corner
    for (int y = 0; y < sample_size && y < height; y++) {
        for (int x = width - sample_size; x < width; x++) {
            if (x >= 0) {
                int idx = (y * width + x) * 3;
                r_sum += data[idx];
                g_sum += data[idx + 1];
                b_sum += data[idx + 2];
                count++;
            }
        }
    }
    
    *bg_r = r_sum / count;
    *bg_g = g_sum / count;
    *bg_b = b_sum / count;
}

// Flood fill starting from top and upper borders to clear light background to white
void flood_fill_background(unsigned char *data, int width, int height, int threshold) {
    int bg_r = 0, bg_g = 0, bg_b = 0;
    get_average_bg(data, width, height, &bg_r, &bg_g, &bg_b);
    
    unsigned char *visited = calloc(width * height, 1);
    if (!visited) {
        fprintf(stderr, "Error: Memory allocation failed for visited array\n");
        return;
    }
    
    Point *queue = malloc(sizeof(Point) * width * height);
    if (!queue) {
        fprintf(stderr, "Error: Memory allocation failed for queue array\n");
        free(visited);
        return;
    }
    
    int head = 0;
    int tail = 0;
    
    // Enqueue top border pixels if they are similar to background color
    for (int x = 0; x < width; x++) {
        int idx = (0 * width + x) * 3;
        double dist = sqrt(pow(data[idx] - bg_r, 2) + 
                           pow(data[idx + 1] - bg_g, 2) + 
                           pow(data[idx + 2] - bg_b, 2));
        if (dist < threshold) {
            queue[tail++] = (Point){x, 0};
            visited[0 * width + x] = 1;
        }
    }
    
    // Enqueue top 10% of left and right border pixels
    int border_h = height / 10;
    if (border_h < 1) border_h = 1;
    for (int y = 1; y < border_h; y++) {
        // Left border
        int idx_l = (y * width + 0) * 3;
        double dist_l = sqrt(pow(data[idx_l] - bg_r, 2) + 
                             pow(data[idx_l + 1] - bg_g, 2) + 
                             pow(data[idx_l + 2] - bg_b, 2));
        if (dist_l < threshold && !visited[y * width + 0]) {
            queue[tail++] = (Point){0, y};
            visited[y * width + 0] = 1;
        }
        
        // Right border
        int idx_r = (y * width + (width - 1)) * 3;
        double dist_r = sqrt(pow(data[idx_r] - bg_r, 2) + 
                             pow(data[idx_r + 1] - bg_g, 2) + 
                             pow(data[idx_r + 2] - bg_b, 2));
        if (dist_r < threshold && !visited[y * width + (width - 1)]) {
            queue[tail++] = (Point){width - 1, y};
            visited[y * width + (width - 1)] = 1;
        }
    }
    
    int dx[] = {0, 0, 1, -1};
    int dy[] = {1, -1, 0, 0};
    
    while (head < tail) {
        Point p = queue[head++];
        
        int idx = (p.y * width + p.x) * 3;
        data[idx] = 255;
        data[idx + 1] = 255;
        data[idx + 2] = 255;
        
        for (int i = 0; i < 4; i++) {
            int nx = p.x + dx[i];
            int ny = p.y + dy[i];
            
            if (nx >= 0 && nx < width && ny >= 0 && ny < height) {
                int n_idx = (ny * width + nx) * 3;
                if (!visited[ny * width + nx]) {
                    double dist = sqrt(pow(data[n_idx] - bg_r, 2) + 
                                       pow(data[n_idx + 1] - bg_g, 2) + 
                                       pow(data[n_idx + 2] - bg_b, 2));
                    if (dist < threshold) {
                        visited[ny * width + nx] = 1;
                        queue[tail++] = (Point){nx, ny};
                    }
                }
            }
        }
    }
    
    free(visited);
    free(queue);
}

char *generate_output_path(const char *input) {
    const char *dot = strrchr(input, '.');
    const char *slash1 = strrchr(input, '\\');
    const char *slash2 = strrchr(input, '/');
    const char *last_slash = (slash1 > slash2) ? slash1 : slash2;
    
    int len = strlen(input);
    char *out = NULL;
    if (dot && dot > last_slash) {
        int base_len = dot - input;
        out = malloc(base_len + 20);
        if (out) {
            strncpy(out, input, base_len);
            out[base_len] = '\0';
            strcat(out, "_processed.jpg");
        }
    } else {
        out = malloc(len + 20);
        if (out) {
            strcpy(out, input);
            strcat(out, "_processed.jpg");
        }
    }
    return out;
}

int main(int argc, char **argv) {
    int threshold = 45;
    int target_width = -1;
    int target_height = -1;
    int verify_x = -1;
    int verify_y = -1;
    char *input_path = NULL;
    char *output_path = NULL;
    
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--threshold") == 0) {
            if (i + 1 < argc) {
                threshold = atoi(argv[++i]);
            } else {
                fprintf(stderr, "Error: --threshold requires a value\n");
                return 1;
            }
        } else if (strcmp(argv[i], "--width") == 0) {
            if (i + 1 < argc) {
                target_width = atoi(argv[++i]);
            } else {
                fprintf(stderr, "Error: --width requires a value\n");
                return 1;
            }
        } else if (strcmp(argv[i], "--height") == 0) {
            if (i + 1 < argc) {
                target_height = atoi(argv[++i]);
            } else {
                fprintf(stderr, "Error: --height requires a value\n");
                return 1;
            }
        } else if (strcmp(argv[i], "--verify-pixel") == 0) {
            if (i + 2 < argc) {
                verify_x = atoi(argv[++i]);
                verify_y = atoi(argv[++i]);
            } else {
                fprintf(stderr, "Error: --verify-pixel requires x and y coordinates\n");
                return 1;
            }
        } else if (argv[i][0] == '-') {
            fprintf(stderr, "Error: Unknown argument %s\n", argv[i]);
            return 1;
        } else {
            if (!input_path) {
                input_path = argv[i];
            } else if (!output_path) {
                output_path = argv[i];
            } else {
                fprintf(stderr, "Error: Too many positional arguments\n");
                return 1;
            }
        }
    }
    
    if (!input_path) {
        fprintf(stderr, "Usage: %s [options] <input_path> [output_path]\n", argv[0]);
        fprintf(stderr, "Options:\n");
        fprintf(stderr, "  --threshold <int>  Tolerance for background similarity (default: 45)\n");
        fprintf(stderr, "  --width <px>       Target width (default: 50%% of original)\n");
        fprintf(stderr, "  --height <px>      Target height (default: 50%% of original)\n");
        return 1;
    }
    
    int width, height, channels;
    // Force loaded as RGB 3-channels
    unsigned char *img_data = stbi_load(input_path, &width, &height, &channels, 3);
    if (!img_data) {
        fprintf(stderr, "Error: Failed to load image %s\n", input_path);
        return 1;
    }
    
    // Calculate destination dimensions
    int dest_w = (target_width > 0) ? target_width : (width / 2);
    int dest_h = (target_height > 0) ? target_height : (height / 2);
    if (dest_w < 1) dest_w = 1;
    if (dest_h < 1) dest_h = 1;
    
    printf("Original: %dx%d, Resizing to: %dx%d\n", width, height, dest_w, dest_h);
    
    // Step 1: Remove background to white using Flood Fill on the original image (higher resolution background details)
    printf("Running background removal flood fill (threshold: %d)...\n", threshold);
    flood_fill_background(img_data, width, height, threshold);
    
    // Step 2: Resize processed image using bilinear interpolation
    unsigned char *resized_data = malloc(dest_w * dest_h * 3);
    if (!resized_data) {
        fprintf(stderr, "Error: Memory allocation failed for resized image\n");
        stbi_image_free(img_data);
        return 1;
    }
    printf("Performing bilinear resize...\n");
    resize_bilinear(img_data, width, height, resized_data, dest_w, dest_h);
    
    if (verify_x >= 0 && verify_y >= 0) {
        if (verify_x < dest_w && verify_y < dest_h) {
            int idx = (verify_y * dest_w + verify_x) * 3;
            printf("VERIFY_PIXEL: R=%d, G=%d, B=%d\n", resized_data[idx], resized_data[idx + 1], resized_data[idx + 2]);
        } else {
            fprintf(stderr, "Error: Verify coordinates %d,%d out of bounds for resized %dx%d\n", verify_x, verify_y, dest_w, dest_h);
        }
    }
    
    printf("Running iterative compression loop...\n");
    int quality = 90;
    MemoryBuffer buf = {NULL, 0, 0, 0};
    
    while (quality >= 10) {
        if (buf.data) {
            free(buf.data);
            buf.data = NULL;
            buf.size = 0;
            buf.capacity = 0;
            buf.has_error = 0;
        }
        
        int success = stbi_write_jpg_to_func(write_to_memory, &buf, dest_w, dest_h, 3, resized_data, quality);
        if (!success || buf.has_error) {
            fprintf(stderr, "Error: JPEG compression callback failed\n");
            break;
        }
        
        printf("Quality: %d -> Size: %.2f KB\n", quality, buf.size / 1024.0);
        if (buf.size < 51200) { // Under 50 KB
            break;
        }
        
        quality -= 5;
    }
    
    char *final_output = output_path ? output_path : generate_output_path(input_path);
    if (!final_output) {
        fprintf(stderr, "Error: Out of memory constructing output path\n");
        free(resized_data);
        stbi_image_free(img_data);
        if (buf.data) free(buf.data);
        return 1;
    }
    
    printf("Writing final image to %s (Quality used: %d)...\n", final_output, quality);
    FILE *f = fopen(final_output, "wb");
    if (!f) {
        fprintf(stderr, "Error: Could not open output file %s for writing\n", final_output);
        free(resized_data);
        stbi_image_free(img_data);
        if (buf.data) free(buf.data);
        if (!output_path) free(final_output);
        return 1;
    }
    
    fwrite(buf.data, 1, buf.size, f);
    fclose(f);
    
    printf("Success! Final size: %.2f KB\n", buf.size / 1024.0);
    
    free(resized_data);
    stbi_image_free(img_data);
    if (buf.data) free(buf.data);
    if (!output_path) free(final_output);
    
    return 0;
}
