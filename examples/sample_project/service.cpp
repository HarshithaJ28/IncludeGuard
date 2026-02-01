#include <vector>
#include <string>
#include <algorithm>
#include <iostream>

class Service {
public:
    void process(const std::vector<std::string>& data) {
        // Uses full vector functionality
        for (const auto& item : data) {
            std::cout << item << std::endl;
        }
    }
};
