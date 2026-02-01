#ifndef DATABASE_H
#define DATABASE_H

#include <string>
#include <vector>
#include <map>

class Database {
public:
    void connect(const std::string& host);
    std::vector<std::string> query(const std::string& sql);
    
private:
    std::map<std::string, std::string> config_;
};

#endif
