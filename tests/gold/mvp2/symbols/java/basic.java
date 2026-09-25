package com.example.crm;

import java.util.List;
import java.util.Optional;
import org.springframework.stereotype.Service;

/**
 * Basic Spring Boot Service Gold Fixture for Java Symbol Extraction.
 */
@Service
public class UserService {

    private final UserRepository userRepository;
    private int retries = 3, timeout = 5000;

    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    public List<UserDTO> findAll() {
        return userRepository.findAll();
    }

    public Optional<UserDTO> findById(Long id) {
        return userRepository.findById(id);
    }

    private void helper() {
        // internal utility
    }
}
